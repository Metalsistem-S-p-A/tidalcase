import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { TranslateModule } from '@ngx-translate/core';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { SkeletonModule } from 'primeng/skeleton';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { TranslateService } from '@ngx-translate/core';
import { AdminTideService } from '../../../services/admin-tide.service';
import { TideInstance } from '@/app/services/tide.service';

@Component({
    selector: 'app-admin-instances',
    standalone: true,
    imports: [CommonModule, TableModule, ButtonModule, TagModule, SkeletonModule, CardModule, ToastModule, ConfirmDialogModule, TranslateModule, TooltipModule],
    providers: [MessageService, ConfirmationService],
    templateUrl: './admin-instances.html'
})
export class AdminInstances implements OnInit {
    private service = inject(AdminTideService);
    private messageService = inject(MessageService);
    private confirmationService = inject(ConfirmationService);
    private translate = inject(TranslateService);

    loading = signal(true);
    instances = signal<TideInstance[]>([]);
    deletingId: string | null = null;

    ngOnInit() { this.load(); }

    load() {
        this.loading.set(true);
        this.service.getInstances().subscribe({
            next: (res) => { this.instances.set(res.instances || []); this.loading.set(false); },
            error: () => { this.loading.set(false); }
        });
    }

    confirmDelete(instance: any) {
        this.confirmationService.confirm({
            message: this.translate.instant('admin.instances.confirmDelete', { tide: instance.tide?.display_name, user: instance.user?.username }),
            header: this.translate.instant('admin.instances.confirmDeleteHeader'),
            icon: 'pi pi-exclamation-triangle',
            accept: () => this.delete(instance.id)
        });
    }

    delete(id: string) {
        this.deletingId = id;
        this.service.deleteInstance(id).subscribe({
            next: () => {
                this.deletingId = null;
                this.messageService.add({ severity: 'success', summary: this.translate.instant('common.success'), detail: this.translate.instant('admin.instances.terminated') });
                this.load();
            },
            error: () => {
                this.deletingId = null;
                this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: this.translate.instant('admin.instances.terminateError') });
            }
        });
    }
}
