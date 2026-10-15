import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { SkeletonModule } from 'primeng/skeleton';
import { TableModule } from 'primeng/table';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { TideService, TideEnvVar } from '../../../services/tide.service';

interface EnvRow { key: string; value: string; description?: string; }
interface Preset { key: string; default: string; description: string; }

@Component({
    selector: 'app-admin-tide-env',
    standalone: true,
    imports: [FormsModule, RouterModule, TranslateModule, ButtonModule, CardModule, InputTextModule, SelectModule, SkeletonModule, TableModule, ToastModule, TooltipModule],
    templateUrl: './admin-tide-env.html',
    providers: [MessageService],
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminTideEnv implements OnInit {
    private readonly route = inject(ActivatedRoute);
    private readonly router = inject(Router);
    private readonly tideService = inject(TideService);
    private readonly http = inject(HttpClient);
    private readonly messageService = inject(MessageService);

    readonly loading = signal(true);
    readonly saving = signal(false);
    readonly tideId = signal('');
    readonly tideName = signal('');
    readonly rows = signal<EnvRow[]>([]);
    readonly presets = signal<Preset[]>([]);
    readonly selectedPreset = signal<Preset | null>(null);

    readonly presetOptions = computed(() => {
        const used = new Set(this.rows().map(r => r.key));
        return this.presets()
            .filter(p => !used.has(p.key))
            .map(p => ({ label: `${p.key} — ${p.description}`, value: p }));
    });

    ngOnInit(): void {
        this.tideId.set(this.route.snapshot.paramMap.get('id') || '');
        this.loadAll();
    }

    private loadAll(): void {
        this.loading.set(true);

        this.http.get<{ presets: Preset[] }>('assets/kasm-env-presets.json')
            .subscribe({ next: (res) => this.presets.set(res?.presets || []), error: () => this.presets.set([]) });

        this.tideService.getTides().subscribe({
            next: (res) => {
                const tide = (res.tides || []).find(t => t.id === this.tideId());
                this.tideName.set(tide?.display_name || '');
            },
        });

        this.tideService.getTideEnv(this.tideId()).subscribe({
            next: (res) => {
                this.loading.set(false);
                if (!res.success) return;
                const presetMap = new Map(this.presets().map(p => [p.key, p.description]));
                this.rows.set((res.env || []).map(e => ({ key: e.key, value: e.value, description: presetMap.get(e.key) })));
            },
            error: () => this.loading.set(false),
        });
    }

    addRow(): void {
        this.rows.update(r => [...r, { key: '', value: '' }]);
    }

    addPreset(): void {
        const p = this.selectedPreset();
        if (!p) return;
        this.rows.update(r => [...r, { key: p.key, value: p.default, description: p.description }]);
        this.selectedPreset.set(null);
    }

    removeRow(idx: number): void {
        this.rows.update(r => r.filter((_, i) => i !== idx));
    }

    save(): void {
        const seen = new Set<string>();
        const dupe = this.rows().find(r => {
            const k = r.key.trim();
            if (!k) return false;
            if (seen.has(k)) return true;
            seen.add(k);
            return false;
        });
        if (dupe) {
            this.messageService.add({ severity: 'error', summary: 'Error', detail: `Duplicate key: ${dupe.key}` });
            return;
        }
        this.saving.set(true);
        const payload: TideEnvVar[] = this.rows()
            .map(r => ({ key: r.key.trim(), value: r.value }))
            .filter(e => e.key);
        this.tideService.saveTideEnv(this.tideId(), payload).subscribe({
            next: (res) => {
                this.saving.set(false);
                if (res.success) {
                    this.messageService.add({ severity: 'success', summary: 'Saved', detail: 'Environment updated.' });
                    const presetMap = new Map(this.presets().map(p => [p.key, p.description]));
                    this.rows.set((res.env || []).map(e => ({ key: e.key, value: e.value, description: presetMap.get(e.key) })));
                } else {
                    this.messageService.add({ severity: 'error', summary: 'Error', detail: (res as any).error || 'Save failed' });
                }
            },
            error: (err) => {
                this.saving.set(false);
                this.messageService.add({ severity: 'error', summary: 'Error', detail: err?.error?.error || 'Save failed' });
            },
        });
    }

    cancel(): void {
        this.router.navigate(['/admin/tides']);
    }

    trackRow = (i: number) => i;
}
