import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { Subscription, interval } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ProgressBarModule } from 'primeng/progressbar';
import { SkeletonModule } from 'primeng/skeleton';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToggleButtonModule } from 'primeng/togglebutton';
import { TooltipModule } from 'primeng/tooltip';
import { AgentInstanceStat, AgentService } from '../../../services/agent.service';

function fmtBytes(bytes: number): string {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

type Severity = 'success' | 'warn' | 'danger';

const SEVERITY_COLOR: Record<Severity, string> = {
    success: '#22c55e',
    warn: '#f59e0b',
    danger: '#ef4444',
};

function severityFor(pct: number): Severity {
    if (pct >= 90) return 'danger';
    if (pct >= 70) return 'warn';
    return 'success';
}

const LIVE_REFRESH_MS = 2500;

@Component({
    selector: 'app-admin-agent-detail',
    standalone: true,
    imports: [FormsModule, TranslateModule, ButtonModule, CardModule, ProgressBarModule, SkeletonModule, TableModule, TagModule, ToggleButtonModule, TooltipModule],
    templateUrl: './admin-agent-detail.html',
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminAgentDetail implements OnInit, OnDestroy {
    private readonly route = inject(ActivatedRoute);
    private readonly service = inject(AgentService);

    readonly loading = signal(true);
    readonly error = signal('');
    readonly agentName = signal('');
    readonly instances = signal<AgentInstanceStat[]>([]);
    readonly totalCores = signal<number | undefined>(undefined);
    readonly totalMemoryMb = signal<number | undefined>(undefined);
    readonly live = signal(false);

    readonly avgCpu = computed(() => {
        const list = this.instances();
        if (!list.length) return 0;
        return Math.round(list.reduce((s, i) => s + i.cpu_percent, 0) / list.length);
    });

    readonly totalMemUsedMb = computed(() =>
        Math.round(this.instances().reduce((s, i) => s + i.mem_usage_bytes, 0) / (1024 * 1024))
    );

    readonly ramUsedPercent = computed(() => {
        const total = this.totalMemoryMb();
        if (!total) return 0;
        return Math.min(Math.round((this.totalMemUsedMb() / total) * 100), 100);
    });

    readonly cpuColor = computed(() => SEVERITY_COLOR[severityFor(this.avgCpu())]);
    readonly ramColor = computed(() => SEVERITY_COLOR[severityFor(this.ramUsedPercent())]);

    private agentId = '';
    private liveSub?: Subscription;

    constructor() {
        // Start/stop the auto-refresh loop whenever the "live" toggle flips.
        effect(() => {
            const on = this.live();
            this.stopLive();
            if (on) {
                this.liveSub = interval(LIVE_REFRESH_MS).subscribe(() => this.load(true));
            }
        });
    }

    ngOnInit(): void {
        this.agentId = this.route.snapshot.paramMap.get('id') || '';
        this.load();
    }

    ngOnDestroy(): void {
        this.stopLive();
    }

    private stopLive(): void {
        this.liveSub?.unsubscribe();
        this.liveSub = undefined;
    }

    load(silent = false): void {
        if (!silent) this.loading.set(true);
        this.error.set('');
        this.service.getAgentStats(this.agentId).subscribe({
            next: (res) => {
                this.loading.set(false);
                if (res.success) {
                    this.agentName.set(res.agent_name || '');
                    this.instances.set(res.instances || []);
                    this.totalCores.set(res.total_cores);
                    this.totalMemoryMb.set(res.total_memory);
                } else if (!silent) {
                    this.error.set(res.error || 'Error');
                }
            },
            error: (err) => {
                this.loading.set(false);
                if (!silent) this.error.set(err?.error?.error || 'Connection error');
            },
        });
    }

    trackInstance = (_: number, item: AgentInstanceStat) => item.instance_id;

    cpuBarValue(inst: AgentInstanceStat): number {
        return Math.min(inst.cpu_percent, 100);
    }

    cpuSeverity(inst: AgentInstanceStat): Severity {
        return severityFor(inst.cpu_percent);
    }

    memPercent(inst: AgentInstanceStat): number {
        if (!inst.mem_limit_bytes) return 0;
        return Math.round((inst.mem_usage_bytes / inst.mem_limit_bytes) * 100);
    }

    memSeverity(inst: AgentInstanceStat): Severity {
        return severityFor(this.memPercent(inst));
    }

    fmtBytes(bytes: number): string {
        return fmtBytes(bytes);
    }
}
