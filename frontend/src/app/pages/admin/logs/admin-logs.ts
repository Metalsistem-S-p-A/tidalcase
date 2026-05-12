import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, model, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { PaginatorModule } from 'primeng/paginator';
import { SelectModule } from 'primeng/select';
import { SkeletonModule } from 'primeng/skeleton';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { LogEntry, LogService } from '../../../services/log.service';

@Component({
    selector: 'app-admin-logs',
    imports: [CommonModule, FormsModule, TableModule, TagModule, SkeletonModule, CardModule, PaginatorModule, SelectModule, ButtonModule, TranslateModule],
    templateUrl: './admin-logs.html'
})
export class AdminLogs implements OnInit {
    private logService = inject(LogService);

    loading = signal(true);
    logs = signal<LogEntry[]>([]);
    totalRecords = model(0);
    page = model(1);
    perPage = model(50);
    selectedLevel: string | null = null;

    levelOptions = [
        { label: 'Tutti', value: null },
        { label: 'INFO', value: 'INFO' },
        { label: 'WARNING', value: 'WARNING' },
        { label: 'ERROR', value: 'ERROR' },
        { label: 'DEBUG', value: 'DEBUG' },
    ];

    ngOnInit() { this.load(); }

    load() {
        this.loading.set(true);
        this.logService.getLogs(this.page(), this.perPage(), this.selectedLevel || undefined).subscribe({
            next: (res) => {
                this.logs.set(res.logs || []);
                this.totalRecords.set(res.pagination?.total || 0);
                this.loading.set(false);
            },
            error: () => { this.loading.set(false); }
        });
    }

    onPageChange(event: any) {
        this.page.set(Math.floor(event.first / event.rows) + 1);
        this.perPage.set(event.rows);
        this.load();
    }

    getLevelSeverity(level: string): 'info' | 'success' | 'warn' | 'danger' | 'secondary' {
        const map: any = { INFO: 'info', WARNING: 'warn', ERROR: 'danger', DEBUG: 'secondary' };
        return map[level] || 'secondary';
    }
}
