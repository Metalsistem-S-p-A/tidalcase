import { CommonModule, Location } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subscription, interval } from 'rxjs';
import { catchError, of, switchMap } from 'rxjs';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { ProgressBarModule } from 'primeng/progressbar';
import { SkeletonModule } from 'primeng/skeleton';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { LanguageService } from '../../services/language.service';
import { RequestInstancePayload, Tide, TideService } from '../../services/tide.service';

@Component({
    selector: 'app-tides',
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [CommonModule, FormsModule, CardModule, ButtonModule, DialogModule, TagModule, SkeletonModule, ToastModule, TranslateModule, TooltipModule, InputTextModule, ProgressBarModule],
    providers: [MessageService],
    templateUrl: './tides.html'
})
export class Tides implements OnInit, OnDestroy {
    private tideService = inject(TideService);
    private languageService = inject(LanguageService);
    private messageService = inject(MessageService);
    private translate = inject(TranslateService);
    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private location = inject(Location);

    loading = signal(true);
    tides = signal<Tide[]>([]);
    launching = signal(false);
    launchingId = signal<string | null>(null);

    connectDialogVisible = signal(false);
    private pendingInstanceId = signal<string | null>(null);

    credentialsDialogVisible = signal(false);
    pendingTide = signal<Tide | null>(null);
    credentialsUsername = signal('');
    credentialsPassword = signal('');
    credentialsDomain = signal('');

    pulling = signal(false);
    pullPercent = signal(0);
    pullLayersDone = signal(0);
    pullLayersTotal = signal(0);
    private pullAgentId = '';
    private pullImage = '';
    private pullSubscription?: Subscription;

    ngOnInit() {
        this.loadTides();
    }

    ngOnDestroy() {
        this.pullSubscription?.unsubscribe();
    }

    loadTides() {
        this.loading.set(true);
        this.tideService.getTides().subscribe({
            next: (res) => {
                this.tides.set(res.tides || []);
                
                const start = this.route.snapshot.queryParamMap.get('start');
                if (start) {
                    this.location.replaceState('/tides');
                    const tide = this.tides().find(t => t.id === start);
                    if(tide) {
                        sessionStorage.setItem('auto_start_done', '1');
                        this.launch(tide);
                    }
                }

                this.loading.set(false);
            },
            error: () => { this.loading.set(false); }
        });
    }

    launch(tide: Tide) {
        if (tide.requires_credentials) {
            this.pendingTide.set(tide);
            this.credentialsUsername.set(tide.connection_settings?.["username"] || '');
            this.credentialsPassword.set(tide.connection_settings?.["password"] || '');
            this.credentialsDomain.set(tide.connection_settings?.["domain"] || '');
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
                    if (res.open_mode && res.open_mode != 'user') {
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

    openSession(mode: string) {
        const instanceId = this.pendingInstanceId();
        this.connectDialogVisible.set(false);
        if (!instanceId) return;
        if (mode === 'current') {
            this.router.navigate(['/session', instanceId], { queryParams: {mode: "current"}});
        } else {
            const url = '/session/' + instanceId;
            const opts = mode === 'window' ? 'width=1280,height=800,noopener,noreferrer' : 'noopener,noreferrer';
            window.open(url, '_blank', opts);
        }
    }

    getTypeIcon(type: string): string {
        const map: Record<string, string> = { container: 'pi pi-desktop', vnc: 'pi pi-window-maximize', rdp: 'pi pi-microsoft', ssh: 'pi pi-code' };
        return map[type] ?? 'pi pi-desktop';
    }

    getTypeSeverity(type: string): 'info' | 'success' | 'warn' | 'danger' | 'secondary' {
        const map: any = { container: 'info', vnc: 'success', rdp: 'warn', ssh: 'secondary' };
        return map[type] || 'secondary';
    }
}
