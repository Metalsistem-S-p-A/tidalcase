import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { CheckboxModule } from 'primeng/checkbox';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { SkeletonModule } from 'primeng/skeleton';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { TextareaModule } from 'primeng/textarea';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { StorageProvider, StorageService } from '../../../services/storage.service';

const DEFAULT_TEMPLATES: Record<string, object> = {
    local:     { driver: 'local', driver_opts: {} },
    rclone:    { driver: 'rclone', driver_opts: { type: 'rclone-type', 'rclone-type': 'sftp', host: '', user: '' } },
    s3:        { driver: 'rclone', driver_opts: { type: 's3', 's3-provider': 'AWS', 's3-env-auth': 'false', 's3-region': 'us-east-1', 's3-access-key-id': '', 's3-secret-access-key': '', uid: '1000', gid: '1000' } },
    gdrive:    { driver: 'rclone', driver_opts: { type: 'drive', 'drive-client-id': '', 'drive-client-secret': '', 'drive-token': '', uid: '1000', gid: '1000' } },
    onedrive:  { driver: 'rclone', driver_opts: { type: 'onedrive', 'onedrive-client-id': '', 'onedrive-client-secret': '', 'onedrive-token': '', uid: '1000', gid: '1000' } },
    nextcloud: { driver: 'rclone', driver_opts: { type: 'webdav', url: 'https://nextcloud.example.com/remote.php/dav/files/username', vendor: 'nextcloud', user: '', pass: '' } },
};

@Component({
    selector: 'app-admin-storage',
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [FormsModule, TableModule, ButtonModule, TagModule, SkeletonModule, CardModule, ToastModule, ConfirmDialogModule, DialogModule, InputTextModule, TextareaModule, CheckboxModule, SelectModule, TooltipModule, TranslateModule],
    providers: [MessageService, ConfirmationService],
    templateUrl: './admin-storage.html',
})
export class AdminStorage implements OnInit {
    private service = inject(StorageService);
    private messageService = inject(MessageService);
    private confirmationService = inject(ConfirmationService);
    private translate = inject(TranslateService);

    loading = signal(true);
    saving = signal(false);
    providers = signal<StorageProvider[]>([]);

    showDialog = signal(false);
    isNew = signal(false);
    editingProvider: Partial<StorageProvider> & { _volumeConfigStr?: string } = {};

    readonly providerTypes = [
        { label: 'Local (Docker volume)', value: 'local' },
        { label: 'S3 (rclone)',           value: 's3' },
        { label: 'Google Drive (rclone)', value: 'gdrive' },
        { label: 'OneDrive (rclone)',     value: 'onedrive' },
        { label: 'Nextcloud / WebDAV',    value: 'nextcloud' },
        { label: 'rclone (custom)',        value: 'rclone' },
    ];

    ngOnInit() { this.load(); }

    load() {
        this.loading.set(true);
        this.service.getProviders().subscribe({
            next: (res) => { this.providers.set(res.providers || []); this.loading.set(false); },
            error: () => { this.loading.set(false); },
        });
    }

    openNew() {
        this.editingProvider = {
            enabled: true,
            provider_type: 's3',
            default_destination: '/storage',
            volume_config: {},
            _volumeConfigStr: JSON.stringify(DEFAULT_TEMPLATES['s3'], null, 2),
        };
        this.isNew.set(true);
        this.showDialog.set(true);
    }

    openEdit(p: StorageProvider) {
        this.editingProvider = {
            ...p,
            _volumeConfigStr: JSON.stringify(p.volume_config || {}, null, 2),
        };
        this.isNew.set(false);
        this.showDialog.set(true);
    }

    onTypeChange(type: string) {
        const tpl = DEFAULT_TEMPLATES[type];
        if (tpl) {
            this.editingProvider._volumeConfigStr = JSON.stringify(tpl, null, 2);
        }
    }

    save() {
        let volume_config: Record<string, unknown>;
        try {
            volume_config = JSON.parse(this.editingProvider._volumeConfigStr || '{}');
        } catch {
            this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: this.translate.instant('admin.storage.invalidJson') });
            return;
        }
        this.saving.set(true);
        this.service.saveProvider({
            id: this.isNew() ? undefined : this.editingProvider.id,
            display_name: this.editingProvider.display_name,
            enabled: this.editingProvider.enabled,
            provider_type: this.editingProvider.provider_type,
            default_destination: this.editingProvider.default_destination,
            volume_config,
        }).subscribe({
            next: (res) => {
                this.saving.set(false);
                if (res.success) {
                    this.showDialog.set(false);
                    this.messageService.add({ severity: 'success', summary: this.translate.instant('common.saved'), detail: this.translate.instant('admin.storage.saved') });
                    this.load();
                } else {
                    this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: res.error || this.translate.instant('admin.storage.saveError') });
                }
            },
            error: (err) => {
                this.saving.set(false);
                this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: err?.error?.error || this.translate.instant('admin.storage.saveError') });
            },
        });
    }

    confirmDelete(p: StorageProvider) {
        this.confirmationService.confirm({
            message: this.translate.instant('admin.storage.confirmDelete', { name: p.display_name }),
            header: this.translate.instant('admin.storage.confirmDeleteHeader'),
            icon: 'pi pi-exclamation-triangle',
            accept: () => this.delete(p.id!),
        });
    }

    delete(id: string) {
        this.service.deleteProvider(id).subscribe({
            next: () => { this.messageService.add({ severity: 'success', summary: this.translate.instant('common.deleted'), detail: this.translate.instant('admin.storage.deleted') }); this.load(); },
            error: () => { this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: this.translate.instant('admin.storage.deleteError') }); },
        });
    }

    typeLabel(type: string): string {
        return this.providerTypes.find(t => t.value === type)?.label ?? type;
    }
}
