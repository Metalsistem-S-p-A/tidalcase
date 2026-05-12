import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ChipModule } from 'primeng/chip';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { SkeletonModule } from 'primeng/skeleton';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { AdminTideService } from '../../../services/admin-tide.service';
import { Registry, RegistryService } from '../../../services/registry.service';

@Component({
    selector: 'app-admin-registry',
    imports: [
        CommonModule, FormsModule, TableModule, ButtonModule, TagModule,
        SkeletonModule, CardModule, ToastModule, ConfirmDialogModule,
        DialogModule, InputTextModule, TranslateModule, TooltipModule,
        SelectModule, ChipModule,
    ],
    providers: [MessageService, ConfirmationService],
    templateUrl: './admin-registry.html',
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminRegistry implements OnInit {
    private readonly registryService = inject(RegistryService);
    private readonly adminTideService = inject(AdminTideService);
    private readonly messageService = inject(MessageService);
    private readonly confirmationService = inject(ConfirmationService);
    private readonly translate = inject(TranslateService);

    readonly loading = signal(true);
    readonly registries = signal<Registry[]>([]);
    readonly registryLocked = signal(false);

    readonly showAddDialog = signal(false);
    readonly newRegistryUrl = signal('');

    // Browse dialog
    readonly selectedRegistry = signal<Registry | null>(null);
    readonly showBrowseDialog = signal(false);
    readonly workspaceFilter = signal('');

    readonly filteredWorkspaces = computed(() => {
        const filter = this.workspaceFilter().toLowerCase();
        const reg = this.selectedRegistry();
        const workspaces: any[] = reg?.tides ?? [];
        if (!filter) return workspaces;
        return workspaces.filter(w =>
            (w.friendly_name ?? '').toLowerCase().includes(filter) ||
            (w.description ?? '').toLowerCase().includes(filter) ||
            (w.categories ?? []).some((c: string) => c.toLowerCase().includes(filter))
        );
    });

    // Import dialog
    readonly showImportDialog = signal(false);
    readonly importingWorkspace = signal<any | null>(null);
    readonly importDisplayName = signal('');
    readonly compatibilityOptions = signal<{ label: string; value: any }[]>([]);
    readonly selectedCompatibility = signal<any | null>(null);
    readonly importing = signal(false);

    ngOnInit() {
        this.load();
    }

    load() {
        this.loading.set(true);
        this.registryService.getRegistries().subscribe({
            next: (res) => {
                this.registries.set(res.registry ?? []);
                this.registryLocked.set(res.registry_locked);
                this.loading.set(false);
            },
            error: () => { this.loading.set(false); }
        });
    }

    addRegistry() {
        const url = this.newRegistryUrl();
        if (!url) return;
        this.loading.set(true);
        this.registryService.addRegistry(url).subscribe({
            next: (res) => {
                this.loading.set(false);
                if (res.success) {
                    this.showAddDialog.set(false);
                    this.newRegistryUrl.set('');
                    this.messageService.add({ severity: 'success', summary: this.translate.instant('common.added'), detail: this.translate.instant('admin.registry.added') });
                    this.load();
                } else {
                    this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: res.error || this.translate.instant('common.error') });
                }
            },
            error: (err) => {
                this.loading.set(false);
                this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: err?.error?.error || this.translate.instant('common.error') });
            }
        });
    }

    confirmDelete(registry: Registry) {
        this.confirmationService.confirm({
            message: this.translate.instant('admin.registry.confirmDelete', { url: registry.url }),
            header: this.translate.instant('admin.registry.confirmDeleteHeader'),
            icon: 'pi pi-exclamation-triangle',
            accept: () => this.deleteRegistry(registry.id!)
        });
    }

    deleteRegistry(id: string | number) {
        this.registryService.deleteRegistry(id).subscribe({
            next: () => {
                this.messageService.add({ severity: 'success', summary: this.translate.instant('common.removed'), detail: this.translate.instant('admin.registry.removed') });
                this.load();
            },
            error: () => { this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: this.translate.instant('admin.registry.removeError') }); }
        });
    }

    browseRegistry(registry: Registry) {
        this.selectedRegistry.set(registry);
        this.workspaceFilter.set('');
        this.showBrowseDialog.set(true);
    }

    openImportDialog(workspace: any) {
        this.importingWorkspace.set(workspace);
        this.importDisplayName.set(workspace.friendly_name ?? '');
        const compatibility: any[] = workspace.compatibility ?? [];
        const options = compatibility.map(c => ({
            label: `${c.version} — ${c.image}`,
            value: c
        }));
        this.compatibilityOptions.set(options);
        this.selectedCompatibility.set(options.at(-1)?.value ?? null);
        this.showImportDialog.set(true);
    }

    confirmImport() {
        const workspace = this.importingWorkspace();
        const compat = this.selectedCompatibility();
        const displayName = this.importDisplayName().trim();
        if (!workspace || !compat || !displayName) return;

        this.importing.set(true);
        this.adminTideService.saveTide({
            id: null as any,
            image_path: this.selectedRegistry()?.url + '/icons/' + workspace.image_src,
            display_name: displayName,
            description: workspace.description ?? '',
            tide_type: 'container',
            container_docker_image: compat.image,
            container_docker_registry: workspace.docker_registry ?? '',
            container_cores: 2,
            container_memory: "2g",
        }).subscribe({
            next: (res) => {
                this.importing.set(false);
                if (res.success) {
                    this.messageService.add({ severity: 'success', summary: this.translate.instant('common.success'), detail: this.translate.instant('admin.registry.tideImported') });
                    this.showImportDialog.set(false);
                    this.showBrowseDialog.set(false);
                } else {
                    this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: res.error || this.translate.instant('common.error') });
                }
            },
            error: (err) => {
                this.importing.set(false);
                this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: err?.error?.error || this.translate.instant('common.error') });
            }
        });
    }
}
