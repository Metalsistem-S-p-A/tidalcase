import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TranslateModule, TranslatePipe, TranslateService } from '@ngx-translate/core';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputTextModule } from 'primeng/inputtext';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { SelectButtonModule } from 'primeng/selectbutton';
import { SelectModule } from 'primeng/select';
import { AdminTideService } from '../../../services/admin-tide.service';
import { Group, GroupService } from '../../../services/group.service';
import { Tide } from '../../../services/tide.service';

interface PermissionRow {
    label: string;
    viewKey: string | null;
    editKey: string;
}

@Component({
    selector: 'app-groups',
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [
        ReactiveFormsModule,
        TranslateModule,
        ButtonModule,
        TableModule,
        DialogModule,
        InputTextModule,
        InputNumberModule,
        CheckboxModule,
        TagModule,
        ConfirmDialogModule,
        TooltipModule,
        SelectButtonModule,
        SelectModule,
        TranslatePipe
    ],
    templateUrl: './groups.html'
})
export class GroupsComponent implements OnInit {
    private readonly groupService = inject(GroupService);
    private readonly adminTideService = inject(AdminTideService);
    private readonly messageService = inject(MessageService);
    private readonly confirmationService = inject(ConfirmationService);
    private readonly translate = inject(TranslateService);
    private readonly fb = inject(FormBuilder);

    readonly groups = signal<Group[]>([]);
    readonly availableTides = signal<{ label: string; value: string }[]>([]);
    readonly loading = signal(false);
    readonly saving = signal(false);
    readonly displayDialog = signal(false);
    readonly isNewGroup = signal(false);
    readonly selectedGroup = signal<Group | null>(null);

    readonly permissionRows: PermissionRow[] = [
        { label: 'groups.permissions.instances', viewKey: 'perm_view_instances', editKey: 'perm_edit_instances' },
        { label: 'groups.permissions.users',     viewKey: 'perm_view_users',     editKey: 'perm_edit_users' },
        { label: 'groups.permissions.tides',     viewKey: 'perm_view_tides',     editKey: 'perm_edit_tides' },
        { label: 'groups.permissions.registry',  viewKey: 'perm_view_registry',  editKey: 'perm_edit_registry' },
        { label: 'groups.permissions.groups',    viewKey: 'perm_view_groups',    editKey: 'perm_edit_groups' },
    ];

    stateOptions: any[] = [];

    readonly form = this.fb.group({
        display_name:           ['', Validators.required],
        priority:               [0],
        max_sessions_per_user:  [null as number | null],
        allow_audio:            [null as boolean | null],
        allow_uploads:          [null as boolean | null],
        allow_downloads:        [null as boolean | null],
        auto_start_tide_id:     [null as string | null],
        browser_homepage:       [null as string | null],
        perm_admin_panel:       [false],
        perm_view_instances:    [false],
        perm_edit_instances:    [false],
        perm_view_users:        [false],
        perm_edit_users:        [false],
        perm_view_tides:        [false],
        perm_edit_tides:        [false],
        perm_view_registry:     [false],
        perm_edit_registry:     [false],
        perm_view_groups:       [false],
        perm_edit_groups:       [false],
    });

    ngOnInit(): void {
        this.initOptions();
        this.translate.onLangChange.subscribe(() => this.initOptions());
        this.loadGroups();
        this.loadTides();
    }

    private loadTides(): void {
        this.adminTideService.getTides().subscribe({
            next: (res: { success: boolean; tides: Tide[] }) => {
                const none = { label: this.translate.instant('groups.autoStartTideNone'), value: '' };
                const tides = (res.tides || []).map((t: Tide) => ({ label: t.display_name, value: t.id }));
                this.availableTides.set([none, ...tides]);
            },
            error: () => {}
        });
    }

    private initOptions() {
        this.stateOptions = [
            { value: null, label: "-"},
            { value: true, label: this.translate.instant("yes")},
            { value: false, label: this.translate.instant("no")}
        ];
    }

    loadGroups(): void {
        this.loading.set(true);
        this.groupService.getGroups().subscribe({
            next: (response) => {
                this.groups.set(response.data ?? []);
                this.loading.set(false);
            },
            error: () => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translate.instant('common.error'),
                    detail: this.translate.instant('groups.errors.loadFailed')
                });
                this.loading.set(false);
            }
        });
    }

    showCreateDialog(): void {
        this.isNewGroup.set(true);
        this.selectedGroup.set(null);
        this.form.reset({ display_name: '', priority: 0, max_sessions_per_user: null, allow_audio: null, auto_start_tide_id: null, browser_homepage: null });
        this.displayDialog.set(true);
    }

    showEditDialog(group: Group): void {
        this.isNewGroup.set(false);
        this.selectedGroup.set(group);
        this.form.patchValue({
            display_name:          group.display_name,
            priority:              group.priority ?? 0,
            max_sessions_per_user: group.settings?.max_sessions_per_user ?? null,
            allow_audio:           group.settings?.allow_audio ?? null,
            allow_downloads:       group.settings?.allow_downloads ?? null,
            allow_uploads:         group.settings?.allow_uploads ?? null,
            auto_start_tide_id:    group.settings?.auto_start_tide_id ?? null,
            browser_homepage:      group.settings?.browser_homepage ?? null,
            perm_admin_panel:      group.permissions.admin_panel,
            perm_view_instances:   group.permissions.view_instances,
            perm_edit_instances:   group.permissions.edit_instances,
            perm_view_users:       group.permissions.view_users,
            perm_edit_users:       group.permissions.edit_users,
            perm_view_tides:       group.permissions.view_tides,
            perm_edit_tides:       group.permissions.edit_tides,
            perm_view_registry:    group.permissions.view_registry,
            perm_edit_registry:    group.permissions.edit_registry,
            perm_view_groups:      group.permissions.view_groups,
            perm_edit_groups:      group.permissions.edit_groups,
        });
        this.displayDialog.set(true);
    }

    hideDialog(): void {
        this.displayDialog.set(false);
        this.selectedGroup.set(null);
    }

    saveGroup(): void {
        if (this.form.invalid) {
            this.form.markAllAsTouched();
            return;
        }
        const v = this.form.getRawValue();
        this.saving.set(true);

        this.groupService.saveGroup({
            id:                  this.isNewGroup() ? null : this.selectedGroup()!.id,
            display_name:        v.display_name!,
            priority:            v.priority ?? 0,
            settings:            {
                max_sessions_per_user: v.max_sessions_per_user ?? null,
                allow_audio: v.allow_audio ?? null,
                allow_downloads: v.allow_downloads ?? null,
                allow_uploads: v.allow_uploads ?? null,
                auto_start_tide_id: v.auto_start_tide_id || null,
                browser_homepage: v.browser_homepage?.trim() || null,
            },
            perm_admin_panel:    v.perm_admin_panel ?? false,
            perm_view_instances: v.perm_view_instances ?? false,
            perm_edit_instances: v.perm_edit_instances ?? false,
            perm_view_users:     v.perm_view_users ?? false,
            perm_edit_users:     v.perm_edit_users ?? false,
            perm_view_tides:     v.perm_view_tides ?? false,
            perm_edit_tides:     v.perm_edit_tides ?? false,
            perm_view_registry:  v.perm_view_registry ?? false,
            perm_edit_registry:  v.perm_edit_registry ?? false,
            perm_view_groups:    v.perm_view_groups ?? false,
            perm_edit_groups:    v.perm_edit_groups ?? false,
        }).subscribe({
            next: () => {
                this.messageService.add({
                    severity: 'success',
                    summary: this.translate.instant('common.success'),
                    detail: this.translate.instant(this.isNewGroup() ? 'groups.success.created' : 'groups.success.updated')
                });
                this.hideDialog();
                this.loadGroups();
                this.saving.set(false);
            },
            error: (error: { error?: { error?: string } }) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translate.instant('common.error'),
                    detail: error.error?.error ?? this.translate.instant('groups.errors.saveFailed')
                });
                this.saving.set(false);
            }
        });
    }

    deleteGroup(group: Group): void {
        if (group.protected) return;
        this.confirmationService.confirm({
            message: this.translate.instant('groups.confirmDelete', { name: group.display_name }),
            header: this.translate.instant('common.confirmDelete'),
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: this.translate.instant('yes'),
            rejectLabel: this.translate.instant('no'),
            accept: () => {
                this.groupService.deleteGroup(group.id).subscribe({
                    next: () => {
                        this.messageService.add({
                            severity: 'success',
                            summary: this.translate.instant('common.success'),
                            detail: this.translate.instant('groups.success.deleted')
                        });
                        this.loadGroups();
                    },
                    error: (error: { error?: { error?: string } }) => {
                        this.messageService.add({
                            severity: 'error',
                            summary: this.translate.instant('common.error'),
                            detail: error.error?.error ?? this.translate.instant('groups.errors.deleteFailed')
                        });
                    }
                });
            }
        });
    }

    getSummary(group: Group): string {
        const perms = group.permissions;
        const active: string[] = [];
        if (perms.admin_panel)         active.push(this.translate.instant('groups.permissions.adminPanel'));
        if (perms.edit_instances)      active.push(this.translate.instant('groups.permissions.instances'));
        else if (perms.view_instances) active.push(this.translate.instant('groups.permissions.instances') + ' (R)');
        if (perms.edit_users)          active.push(this.translate.instant('groups.permissions.users'));
        else if (perms.view_users)     active.push(this.translate.instant('groups.permissions.users') + ' (R)');
        if (perms.edit_tides)          active.push(this.translate.instant('groups.permissions.tides'));
        else if (perms.view_tides)     active.push(this.translate.instant('groups.permissions.tides') + ' (R)');
        if (perms.edit_registry)       active.push(this.translate.instant('groups.permissions.registry'));
        else if (perms.view_registry)  active.push(this.translate.instant('groups.permissions.registry') + ' (R)');
        if (perms.edit_groups)         active.push(this.translate.instant('groups.permissions.groups'));
        else if (perms.view_groups)    active.push(this.translate.instant('groups.permissions.groups') + ' (R)');
        return active.length ? active.join(', ') : '-';
    }
}
