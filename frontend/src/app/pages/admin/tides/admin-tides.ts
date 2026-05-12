import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { SkeletonModule } from 'primeng/skeleton';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { TextareaModule } from 'primeng/textarea';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { TranslateService } from '@ngx-translate/core';
import { MultiSelectModule } from 'primeng/multiselect';
import { AdminTideService } from '../../../services/admin-tide.service';
import { Group, GroupService } from '../../../services/group.service';
import { StorageMount, StorageProvider, StorageService } from '../../../services/storage.service';
import { Tide } from '../../../services/tide.service';
import { CheckboxModule } from 'primeng/checkbox';
import { JsonEditorComponent } from '../../../components/json-editor/json-editor';

@Component({
    selector: 'app-admin-tides',
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [CommonModule, FormsModule, TableModule, ButtonModule, TagModule, SkeletonModule, CardModule, ToastModule, ConfirmDialogModule, DialogModule, InputTextModule, InputNumberModule, TextareaModule, SelectModule, TranslateModule, TooltipModule, CheckboxModule, MultiSelectModule, JsonEditorComponent],
    providers: [MessageService, ConfirmationService],
    templateUrl: './admin-tides.html'
})
export class AdminTides implements OnInit {
    private service = inject(AdminTideService);
    private storageService = inject(StorageService);
    private groupService = inject(GroupService);
    private messageService = inject(MessageService);
    private confirmationService = inject(ConfirmationService);
    private translate = inject(TranslateService);

    loading = signal(true);
    saving = signal(false);
    uploading = signal(false);
    tides = signal<Tide[]>([]);
    availableProviders = signal<StorageProvider[]>([]);
    availableGroups = signal<Group[]>([]);
    availableAgents = signal<{ id: string; display_name: string }[]>([]);
    storageMounts = signal<StorageMount[]>([]);
    restrictedGroupIds: string[] = [];
    selectedAgentIds: string[] = [];
    selectedAgentId: string | null = null;

    showDialog = signal(false);
    editingTide: Partial<Tide> = {};
    isNew = signal(false);

    readonly tideTypes = [
        { label: 'Container', value: 'container' },
        { label: 'VNC', value: 'vnc' },
        { label: 'RDP', value: 'rdp' },
        { label: 'SSH', value: 'ssh' },
    ];

    openMode: {label: string, value: string}[] = [];

    agentSelectionMode: {label: string, value: string}[] = [];

    ngOnInit() {
        this.load();
        this.loadProviders();
        this.loadGroups();
        this.loadAgents();
        this.initOptions();
        this.translate.onLangChange.subscribe(() => this.initOptions());
    }

    private initOptions() {
        this.agentSelectionMode = [
            { label: this.translate.instant('admin.tides.agent_selection_auto'), value: 'auto' },
            { label: this.translate.instant('admin.tides.agent_selection_rr'), value: 'rr' },
            { label: this.translate.instant('admin.tides.agent_selection_ll'), value: 'll' },
            { label: this.translate.instant('admin.tides.agent_selection_fixed'), value: 'fixed' },
        ];
        this.openMode = [
            { label: this.translate.instant('admin.tides.open_mode_user'), value: 'user' },
            { label: this.translate.instant('admin.tides.open_mode_new_tab'), value: 'tab' },
            { label: this.translate.instant('admin.tides.open_mode_same_tab'), value: 'current' },
            { label: this.translate.instant('admin.tides.open_mode_new_window'), value: 'window' },
        ];
    }

    loadProviders() {
        this.storageService.getProviders().subscribe({
            next: (res) => this.availableProviders.set(res.providers || [])
        });
    }

    loadGroups() {
        this.groupService.getGroups().subscribe({
            next: (res) => this.availableGroups.set(res.data || [])
        });
    }

    loadAgents() {
        this.service.getAgents().subscribe({
            next: (res) => this.availableAgents.set(res.agents || [])
        });
    }

    load() {
        this.loading.set(true);
        this.service.getTides().subscribe({
            next: (res) => { this.tides.set(res.tides || []); this.loading.set(false); },
            error: () => { this.loading.set(false); }
        });
    }

    connectionSettingsJson = '{}';

    openNew() {
        this.editingTide = { tide_type: 'container', container_cores: 2, container_memory: '1g', container_swap: '128m', agent_selection_mode: 'auto', vnc_user: 'kasm_user' };
        this.connectionSettingsJson = '{}';
        this.storageMounts.set([]);
        this.restrictedGroupIds = [];
        this.selectedAgentIds = [];
        this.selectedAgentId = null;
        this.isNew.set(true);
        this.showDialog.set(true);
    }

    openEdit(tide: Tide) {
        this.editingTide = { ...tide };
        this.connectionSettingsJson = JSON.stringify(tide.connection_settings || {}, null, 2);
        this.storageMounts.set([]);
        this.restrictedGroupIds = tide.restricted_groups ? tide.restricted_groups.split(',').filter(Boolean) : [];
        const agentIds = (tide.agents ?? []).map(a => a.id);
        this.selectedAgentIds = agentIds;
        this.selectedAgentId = agentIds[0] ?? null;
        this.isNew.set(false);
        this.showDialog.set(true);
        this.storageService.getMounts(tide.id).subscribe({
            next: (res) => this.storageMounts.set(res.mounts || [])
        });
    }

    save() {
        try {
            this.editingTide.connection_settings = JSON.parse(this.connectionSettingsJson);
        } catch {
            this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: this.translate.instant('admin.tides.connectionSettingsInvalid') });
            return;
        }
        this.saving.set(true);
        const agentIds = this.editingTide.agent_selection_mode === 'fixed'
            ? (this.selectedAgentId ? [this.selectedAgentId] : [])
            : this.selectedAgentIds;
        const payload = { ...this.editingTide, id: this.isNew() ? undefined : this.editingTide.id, restricted_groups: this.restrictedGroupIds, agent: agentIds } as any;
        this.service.saveTide(payload).subscribe({
            next: (res) => {
                if (!res.success) {
                    this.saving.set(false);
                    this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: res.error || this.translate.instant('admin.tides.saveError') });
                    return;
                }
                const tideId = res.tide_id ?? this.editingTide.id!;
                this.storageService.saveMounts(tideId, this.storageMounts()).subscribe({
                    next: (mountRes) => {
                        this.saving.set(false);
                        if (mountRes.success) {
                            this.showDialog.set(false);
                            this.messageService.add({ severity: 'success', summary: this.translate.instant('common.saved'), detail: this.translate.instant('admin.tides.saved') });
                            this.load();
                        } else {
                            this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: mountRes.error || this.translate.instant('admin.tides.mountsSaveError') });
                        }
                    },
                    error: () => {
                        this.saving.set(false);
                        this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: this.translate.instant('admin.tides.mountsSaveError') });
                    }
                });
            },
            error: (err) => {
                this.saving.set(false);
                this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: err?.error?.error || this.translate.instant('admin.tides.saveError') });
            }
        });
    }

    addMount() {
        const providers = this.availableProviders();
        const first = providers[0];
        this.storageMounts.update(m => [...m, {
            storage_provider_id: first?.id ?? '',
            enabled: true,
            read_only: false,
            destination: first?.default_destination ?? '/storage'
        }]);
    }

    removeMount(index: number) {
        this.storageMounts.update(m => m.filter((_, i) => i !== index));
    }

    updateMount(index: number, patch: Partial<StorageMount>) {
        this.storageMounts.update(m => m.map((item, i) => i === index ? { ...item, ...patch } : item));
    }

    onMountProviderChange(index: number, providerId: string) {
        const provider = this.availableProviders().find(p => p.id === providerId);
        this.updateMount(index, {
            storage_provider_id: providerId,
            destination: provider?.default_destination ?? '/storage'
        });
    }

    providerLabel(id: string): string {
        return this.availableProviders().find(p => p.id === id)?.display_name ?? id;
    }

    confirmDelete(tide: Tide) {
        this.confirmationService.confirm({
            message: this.translate.instant('admin.tides.confirmDelete', { name: tide.display_name }),
            header: this.translate.instant('admin.common.confirmDeleteHeader'),
            icon: 'pi pi-exclamation-triangle',
            accept: () => this.delete(tide.id)
        });
    }

    delete(id: string) {
        this.service.deleteTide(id).subscribe({
            next: () => { this.messageService.add({ severity: 'success', summary: this.translate.instant('common.deleted'), detail: this.translate.instant('admin.tides.deleted') }); this.load(); },
            error: () => { this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: this.translate.instant('admin.tides.deleteError') }); }
        });
    }

    triggerFileInput(input: HTMLInputElement) {
        input.value = '';
        input.click();
    }

    onFileSelected(event: Event) {
        const file = (event.target as HTMLInputElement).files?.[0];
        if (!file) return;
        this.uploading.set(true);
        this.service.uploadTideImage(file).subscribe({
            next: (res) => {
                if (res.success) this.editingTide.image_path = res.url;
                else this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: res.error || this.translate.instant('admin.tides.uploadFailed') });
                this.uploading.set(false);
            },
            error: () => {
                this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: this.translate.instant('admin.tides.uploadFailed') });
                this.uploading.set(false);
            }
        });
    }

    getTypeSeverity(type: string): 'info' | 'success' | 'warn' | 'danger' | 'secondary' {
        const map: any = { container: 'info', vnc: 'success', rdp: 'warn', ssh: 'secondary' };
        return map[type] || 'secondary';
    }
}
