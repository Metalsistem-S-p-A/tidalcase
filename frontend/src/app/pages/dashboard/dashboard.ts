import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { forkJoin, of } from 'rxjs';
import { ConfirmationService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { SkeletonModule } from 'primeng/skeleton';
import { TagModule } from 'primeng/tag';
import { AgentService } from '../../services/agent.service';
import { AuthService } from '../../services/auth.service';
import { TideService } from '../../services/tide.service';
import { SessionCardDirective } from './session_card';

@Component({
    selector: 'app-dashboard',
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [CommonModule, RouterModule, CardModule, ButtonModule, ConfirmDialogModule, DialogModule, TagModule, SkeletonModule, TranslateModule, SessionCardDirective],
    providers: [ConfirmationService],
    templateUrl: './dashboard.html'
})
export class Dashboard implements OnInit {
    private tideService = inject(TideService);
    private agentService = inject(AgentService);
    private confirmationService = inject(ConfirmationService);
    private router = inject(Router);
    authService = inject(AuthService);

    loading = signal(true);
    mySessions = signal<any[]>([]);
    availableTidesCount = signal(0);
    agentsCount = signal(0);
    healthyAgentsCount = signal(0);
    runningInstancesCount = computed(() => this.mySessions().length);

    connectDialogVisible = signal(false);
    private pendingInstanceId = signal<string | null>(null);


    ngOnInit() {
        this.loadData();
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
                sess.forEach(s => {
                    const vnc_url = s.vnc_url;
                    if (!vnc_url) return;
                    const base = vnc_url.split('/vnc.html')[0];
                    s.screenshotUrl = `${base}/api/get_screenshot?t=${Date.now()}`
                });

                this.mySessions.set(sess);
                this.availableTidesCount.set((tides.tides || []).length);
                const agentList = agents.agents || [];
                this.agentsCount.set(agentList.length);
                this.healthyAgentsCount.set(agentList.filter((a: any) => a.healthy).length);
                this.loading.set(false);
                this.tryAutoStart(sess);
            },
            error: () => { this.loading.set(false); }
        });
    }

    private tryAutoStart(sessions: any[]): void {
        if (sessionStorage.getItem('auto_start_done')) return;
        const tideId = this.authService.currentUser()?.settings?.['auto_start_tide_id'];
        if (!tideId) return;

        const existing = sessions.find(s => s.tide?.id === tideId);
        if (existing) {
            sessionStorage.setItem('auto_start_done', '1');
            this.connectSession(existing.id);
            return;
        }

        this.router.navigate(['/tides'],  { queryParams: {start: tideId}});
    }

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
    }

    connectSession(instanceId: string) {
        this.pendingInstanceId.set(instanceId);
        const open_mode = this.mySessions().find(s => s.id === instanceId).tide.open_mode
        if (open_mode === 'user') {
            this.connectDialogVisible.set(true);
        }
        else {
            this.openSession(open_mode);
        }
    }

    openSession(mode: 'current' | 'tab' | 'window') {
        const instanceId = this.pendingInstanceId();
        this.connectDialogVisible.set(false);
        if (!instanceId) return;
        if (mode === 'current') {
            this.router.navigate(['/session', instanceId],  { queryParams: {mode: "current"}});
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
