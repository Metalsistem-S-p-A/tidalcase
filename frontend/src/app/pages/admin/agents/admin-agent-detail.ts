import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ChartModule } from 'primeng/chart';
import { ProgressBarModule } from 'primeng/progressbar';
import { SkeletonModule } from 'primeng/skeleton';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { AgentInstanceStat, AgentService } from '../../../services/agent.service';

function fmtBytes(bytes: number): string {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

type Severity = 'success' | 'warn' | 'danger';

@Component({
    selector: 'app-admin-agent-detail',
    standalone: true,
    imports: [RouterLink, TranslateModule, ButtonModule, CardModule, ChartModule, ProgressBarModule, SkeletonModule, TableModule, TagModule, TooltipModule],
    templateUrl: './admin-agent-detail.html',
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminAgentDetail implements OnInit {
    private readonly route = inject(ActivatedRoute);
    private readonly service = inject(AgentService);

    readonly loading = signal(true);
    readonly error = signal('');
    readonly instances = signal<AgentInstanceStat[]>([]);
    readonly totalCores = signal<number | undefined>(undefined);
    readonly totalMemoryMb = signal<number | undefined>(undefined);

    readonly avgCpu = computed(() => {
        const list = this.instances();
        if (!list.length) return 0;
        return Math.round(list.reduce((s, i) => s + i.cpu_percent, 0) / list.length);
    });

    readonly totalMemUsedMb = computed(() =>
        Math.round(this.instances().reduce((s, i) => s + i.mem_usage_bytes, 0) / (1024 * 1024))
    );

    readonly memChartData = computed(() => {
        const list = [...this.instances()].sort((a, b) => b.mem_usage_bytes - a.mem_usage_bytes);
        return {
            labels: list.map(i => i.tide_name || i.container_name),
            datasets: [{
                label: 'RAM (MB)',
                data: list.map(i => Math.round(i.mem_usage_bytes / (1024 * 1024))),
                backgroundColor: '#2a78d6',
                borderRadius: 4,
                barThickness: 18,
            }],
        };
    });

    readonly memChartOptions = {
        indexAxis: 'y' as const,
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { beginAtZero: true },
            y: { grid: { display: false } },
        },
    };

    private agentId = '';

    ngOnInit(): void {
        this.agentId = this.route.snapshot.paramMap.get('id') || '';
        this.load();
    }

    load(): void {
        this.loading.set(true);
        this.error.set('');
        this.service.getAgentStats(this.agentId).subscribe({
            next: (res) => {
                this.loading.set(false);
                if (res.success) {
                    this.instances.set(res.instances || []);
                    this.totalCores.set(res.total_cores);
                    this.totalMemoryMb.set(res.total_memory);
                } else {
                    this.error.set(res.error || 'Error');
                }
            },
            error: (err) => {
                this.loading.set(false);
                this.error.set(err?.error?.error || 'Connection error');
            },
        });
    }

    cpuBarValue(inst: AgentInstanceStat): number {
        return Math.min(inst.cpu_percent, 100);
    }

    cpuSeverity(inst: AgentInstanceStat): Severity {
        if (inst.cpu_percent >= 90) return 'danger';
        if (inst.cpu_percent >= 70) return 'warn';
        return 'success';
    }

    memPercent(inst: AgentInstanceStat): number {
        if (!inst.mem_limit_bytes) return 0;
        return Math.round((inst.mem_usage_bytes / inst.mem_limit_bytes) * 100);
    }

    memSeverity(inst: AgentInstanceStat): Severity {
        const pct = this.memPercent(inst);
        if (pct >= 90) return 'danger';
        if (pct >= 70) return 'warn';
        return 'success';
    }

    fmtBytes(bytes: number): string {
        return fmtBytes(bytes);
    }
}
