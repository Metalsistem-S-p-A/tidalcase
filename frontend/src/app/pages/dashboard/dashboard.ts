import { CommonModule, Location } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subscription, forkJoin, interval, of } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { ProgressBarModule } from 'primeng/progressbar';
import { SkeletonModule } from 'primeng/skeleton';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { AgentService } from '../../services/agent.service';
import { AuthService } from '../../services/auth.service';
import { LanguageService } from '../../services/language.service';
import { RequestInstancePayload, Tide, TideService } from '../../services/tide.service';
import { SessionCardDirective } from './session_card';

@Component({
    selector: 'app-dashboard',
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [CommonModule, FormsModule, RouterModule, CardModule, ButtonModule, ConfirmDialogModule, DialogModule, TagModule, SkeletonModule, ToastModule, TranslateModule, InputTextModule, ProgressBarModule, SessionCardDirective],
    providers: [ConfirmationService, MessageService],
    templateUrl: './dashboard.html'
})
export class Dashboard implements OnInit, OnDestroy {
    private tideService = inject(TideService);
    private agentService = inject(AgentService);
    private confirmationService = inject(ConfirmationService);
    private messageService = inject(MessageService);
    private languageService = inject(LanguageService);
    private translate = inject(TranslateService);
    private router = inject(Router);
    private route = inject(ActivatedRoute);
    private location = inject(Location);
    authService = inject(AuthService);

    loading = signal(true);
    mySessions = signal<any[]>([]);
    tides = signal<Tide[]>([]);
    agentsCount = signal(0);
    healthyAgentsCount = signal(0);
    runningInstancesCount = computed(() => this.mySessions().length);
    availableTidesCount = computed(() => this.tides().length);

    // Session connect dialog
    connectDialogVisible = signal(false);
    private pendingInstanceId = signal<string | null>(null);

    // Launch state
    launching = signal(false);
    launchingId = signal<string | null>(null);

    // Credentials dialog
    credentialsDialogVisible = signal(false);
    pendingTide = signal<Tide | null>(null);
    credentialsUsername = signal('');
    credentialsPassword = signal('');
    credentialsDomain = signal('');

    // Pull state
    pulling = signal(false);
    pullPercent = signal(0);
    pullLayersDone = signal(0);
    pullLayersTotal = signal(0);
    private pullAgentId = '';
    private pullImage = '';
    private pullSubscription?: Subscription;

    ngOnInit() {
        this.loadData();
    }

    ngOnDestroy() {
        this.pullSubscription?.unsubscribe();
    }

    loadData() {
        this.loading.set(true);

        const agents$ = this.authService.isAdmin()
            ? this.agentService.getAgents()
            : of({ agents: [] });

        forkJoin({
            sessions: this.tideService.getMyInstances(),
            tides: this.tideService.getTides(),
            agents: agents$,
        }).subscribe({
            next: ({ sessions, tides, agents }) => {
                const sess = sessions.instances || [];
                sess.forEach((s: any) => {
                    const vnc_url = s.vnc_url;
                    if (!vnc_url) return;
                    const base = vnc_url.split('/vnc.html')[0];
                    s.screenshotUrl = `${base}/api/get_screenshot?t=${Date.now()}`;
                });

                this.mySessions.set(sess);
                const tideList: Tide[] = tides.tides || [];
                this.tides.set(tideList);
                const agentList = agents.agents || [];
                this.agentsCount.set(agentList.length);
                this.healthyAgentsCount.set(agentList.filter((a: any) => a.healthy).length);
                this.loading.set(false);

                // Deep link: /?start=<tide_id> launches that tide once.
                const startId = this.route.snapshot.queryParamMap.get('start');
                if (startId) {
                    this.location.replaceState('/');
                    const tide = tideList.find(t => t.id === startId);
                    if (tide) {
                        sessionStorage.setItem('auto_start_done', '1');
                        this.launch(tide);
                        return;
                    }
                }

                this.tryAutoStart(sess, tideList);
            },
            error: () => { this.loading.set(false); }
        });
    }

    private tryAutoStart(sessions: any[], tideList: Tide[]): void {
        if (sessionStorage.getItem('auto_start_done')) return;
        const tideId = this.authService.currentUser()?.settings?.['auto_start_tide_id'];
        if (!tideId) return;

        const existing = sessions.find((s: any) => s.tide?.id === tideId);
        if (existing) {
            sessionStorage.setItem('auto_start_done', '1');
            this.connectSession(existing.id);
            return;
        }

        const tide = tideList.find(t => t.id === tideId);
        if (tide) {
            sessionStorage.setItem('auto_start_done', '1');
            this.launch(tide);
        }
    }

    // ── Tide launching ────────────────────────────────────────────────────────

    launch(tide: Tide) {
        if (tide.requires_credentials) {
            this.pendingTide.set(tide);
            this.credentialsUsername.set(tide.connection_settings?.['username'] || '');
            this.credentialsPassword.set(tide.connection_settings?.['password'] || '');
            this.credentialsDomain.set(tide.connection_settings?.['domain'] || '');
            this.credentialsDialogVisible.set(true);
            return;
        }
        this.startLaunch(tide);
    }

    submitCredentials() {
        const tide = this.pendingTide();
        if (!tide) return;
        this.credentialsDialogVisible.set(false);
        const credentials: { username?: string; password?: string; domain?: string } = {
            username: this.credentialsUsername() || undefined,
            password: this.credentialsPassword() || undefined,
        };
        if (this.credentialsDomain()) credentials.domain = this.credentialsDomain();
        this.startLaunch(tide, credentials);
    }

    private startLaunch(tide: Tide, credentials?: { username?: string; password?: string; domain?: string }) {
        this.launching.set(true);
        this.launchingId.set(tide.id);
        const payload: RequestInstancePayload = { tide_id: tide.id, language: this.languageService.getCurrentLang() };
        if (credentials) payload.credentials = credentials;
        this.tideService.requestInstance(payload).subscribe({
            next: (res) => {
                this.launching.set(false);
                this.launchingId.set(null);
                if (res.success && res.instance_id) {
                    this.pendingInstanceId.set(res.instance_id);
                    if (res.open_mode && res.open_mode !== 'user') {
                        this.openSession(res.open_mode);
                    } else {
                        this.connectDialogVisible.set(true);
                    }
                } else if (res.pulling) {
                    this.pullAgentId = res.agent_id || '';
                    this.pullImage = res.image || '';
                    this.pullPercent.set(0);
                    this.pullLayersDone.set(0);
                    this.pullLayersTotal.set(0);
                    this.pulling.set(true);
                    this.startPullPolling(tide, credentials);
                } else {
                    this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: res.error || this.translate.instant('tides.launchError') });
                }
            },
            error: (err) => {
                this.launching.set(false);
                this.launchingId.set(null);
                this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: err?.error?.error || this.translate.instant('tides.launchErrorDetail') });
            }
        });
    }

    private startPullPolling(tide: Tide, credentials?: { username?: string; password?: string; domain?: string }) {
        this.pullSubscription?.unsubscribe();
        this.pullSubscription = interval(2500).pipe(
            switchMap(() => this.tideService.getPullStatus(this.pullAgentId, this.pullImage).pipe(
                catchError(() => of({ success: true, status: 'unknown', percent: 0, layers_done: 0, layers_total: 0, error: '' }))
            ))
        ).subscribe(status => {
            if (status.status === 'pulling') {
                this.pullPercent.set(status.percent || 0);
                this.pullLayersDone.set(status.layers_done || 0);
                this.pullLayersTotal.set(status.layers_total || 0);
            } else if (status.status === 'done') {
                this.pullSubscription?.unsubscribe();
                this.pulling.set(false);
                this.startLaunch(tide, credentials);
            } else if (status.status === 'error') {
                this.pullSubscription?.unsubscribe();
                this.pulling.set(false);
                this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: this.translate.instant('tides.launchError') });
            }
        });
    }

    // ── Sessions ──────────────────────────────────────────────────────────────

    screenshotError(id: string) {
        this.mySessions.update(list =>
            list.map(s => s.id === id ? { ...s, screenshotUrl: null } : s)
        );
    }

    onRefresh = (id: string, url: string) => {
        this.mySessions.update(list =>
            list.map(s => s.id === id ? { ...s, screenshotUrl: url } : s)
        );
    };

    onRemove = (id: string) => {
        this.tideService.destroyInstance(id).subscribe({
            complete: () => { this.mySessions.update(list => list.filter(s => s.id !== id)); },
            error: () => { this.mySessions.update(list => list.filter(s => s.id !== id)); }
        });
    };

    connectSession(instanceId: string) {
        this.pendingInstanceId.set(instanceId);
        const open_mode = this.mySessions().find(s => s.id === instanceId)?.tide?.open_mode;
        if (open_mode === 'user' || !open_mode) {
            this.connectDialogVisible.set(true);
        } else {
            this.openSession(open_mode);
        }
    }

    openSession(mode: string) {
        const instanceId = this.pendingInstanceId();
        this.connectDialogVisible.set(false);
        if (!instanceId) return;
        if (mode === 'current') {
            this.router.navigate(['/session', instanceId], { queryParams: { mode: 'current' } });
        } else {
            const url = '/session/' + instanceId;
            const opts = mode === 'window' ? 'width=1280,height=800,noopener,noreferrer' : 'noopener,noreferrer';
            window.open(url, '_blank', opts);
        }
    }

    stopSession(instanceId: string) {
        this.confirmationService.confirm({
            message: 'Terminare la sessione?',
            header: 'Conferma',
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: 'Termina',
            rejectLabel: 'Annulla',
            acceptButtonStyleClass: 'p-button-danger',
            accept: () => {
                this.tideService.destroyInstance(instanceId).subscribe({
                    next: () => this.mySessions.update(list => list.filter(s => s.id !== instanceId)),
                    error: () => {}
                });
            },
        });
    }

    getTypeIcon(type: string): string {
        const map: Record<string, string> = { container: 'pi pi-desktop', vnc: 'pi pi-window-maximize', rdp: 'pi pi-microsoft', ssh: 'pi pi-code' };
        return map[type] ?? 'pi pi-desktop';
    }

    getTimeLimit(session: any): string {
        return this.formatDuration(session.session_time_limit);
    }

    getIdleTimeout(session: any): string {
        return this.formatDuration(session.session_idle_time_limit);
    }

    private formatDuration(totalMinutes: number): string {
        const totalSeconds = Math.max(0, Math.round(totalMinutes * 60));
        const h = Math.floor(totalSeconds / 3600);
        const m = Math.floor((totalSeconds % 3600) / 60);
        const s = totalSeconds % 60;
        const p = (n: number) => n.toFixed(0).padStart(2, '0');
        return `${p(h)}:${p(m)}:${p(s)}`;
    }
}
