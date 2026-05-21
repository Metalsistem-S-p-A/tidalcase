import { ChangeDetectionStrategy, Component, inject, OnInit, signal, viewChild } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { MultiSelectModule } from 'primeng/multiselect';
import { PasswordModule } from 'primeng/password';
import { SelectModule } from 'primeng/select';
import { Table, TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { AdminUserService, TidalcaseUser } from '../../../services/admin-user.service';
import { AdminTideService } from '../../../services/admin-tide.service';
import { Group, GroupService } from '../../../services/group.service';
import { Tide } from '../../../services/tide.service';

@Component({
    selector: 'app-users',
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [
        ReactiveFormsModule,
        TranslateModule,
        ButtonModule,
        TableModule,
        DialogModule,
        InputTextModule,
        PasswordModule,
        MultiSelectModule,
        SelectModule,
        TagModule,
        ConfirmDialogModule,
        IconFieldModule,
        InputIconModule,
    ],
    templateUrl: './users.html'
})
export class UsersComponent implements OnInit {
    private readonly adminUserService = inject(AdminUserService);
    private readonly adminTideService = inject(AdminTideService);
    private readonly groupService = inject(GroupService);
    private readonly messageService = inject(MessageService);
    private readonly confirmationService = inject(ConfirmationService);
    private readonly translateService = inject(TranslateService);
    private readonly fb = inject(FormBuilder);

    readonly table = viewChild<Table>('dt');

    readonly users = signal<TidalcaseUser[]>([]);
    readonly totalRecords = signal(0);
    readonly groups = signal<Group[]>([]);
    readonly loading = signal(false);
    readonly saving = signal(false);
    readonly displayDialog = signal(false);
    readonly isNewUser = signal(false);
    readonly selectedUser = signal<TidalcaseUser | null>(null);

    readonly groupOptions = signal<{ label: string; value: string }[]>([]);
    readonly availableTides = signal<{ label: string; value: string }[]>([]);

    readonly form = this.fb.group({
        username: ['', Validators.required],
        usertype: ['Internal'],
        password: [''],
        groups: [[] as string[]],
        auto_start_tide_id: [null as string | null],
        preferred_language: ''
    });

    readonly usertypeOptions = [
        { label: 'Internal', value: 'Internal' },
        { label: 'External', value: 'External' },
    ];

    readonly languages = [
        { label: 'System', value: 'system' },
        { label: 'English', value: 'en' },
        { label: 'Italiano', value: 'it' }
    ];

    ngOnInit(): void {
        this.loadGroups();
        this.loadUsers();
        this.loadTides();
    }

    private loadTides(): void {
        this.adminTideService.getTides().subscribe({
            next: (res: { success: boolean; tides: Tide[] }) => {
                const none = { label: this.translateService.instant('users.autoStartTideNone'), value: '' };
                const tides = (res.tides || []).map((t: Tide) => ({ label: t.display_name, value: t.id }));
                this.availableTides.set([none, ...tides]);
            },
            error: () => {}
        });
    }

    loadUsers(): void {
        this.loading.set(true);
        this.adminUserService.getUsers().subscribe({
            next: (response) => {
                this.users.set(response.data);
                this.totalRecords.set(response.totalRecords);
                this.loading.set(false);
            },
            error: () => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translateService.instant('common.error'),
                    detail: this.translateService.instant('users.errors.loadFailed')
                });
                this.loading.set(false);
            }
        });
    }

    private loadGroups(): void {
        this.groupService.getGroups().subscribe({
            next: (response) => {
                const data = response.data ?? [];
                this.groups.set(data);
                this.groupOptions.set(data.map(g => ({ label: g.display_name, value: g.id })));
            },
            error: () => { }
        });
    }

    showCreateDialog(): void {
        this.isNewUser.set(true);
        this.selectedUser.set(null);
        this.form.reset({ username: '', usertype: 'Internal', password: '', groups: [], auto_start_tide_id: null, preferred_language: 'system' });
        this.form.controls.username.enable();
        this.form.controls.password.setValidators(Validators.required);
        this.form.controls.password.updateValueAndValidity();
        this.displayDialog.set(true);
    }

    get isExternalUser(): boolean {
        return this.form.controls.usertype.value === 'External';
    }

    onUsertypeChange(): void {
        if (this.isExternalUser) {
            this.form.controls.password.clearValidators();
            this.form.controls.password.setValue('');
        } else {
            this.form.controls.password.setValidators(Validators.required);
        }
        this.form.controls.password.updateValueAndValidity();
    }

    showEditDialog(user: TidalcaseUser): void {
        this.isNewUser.set(false);
        this.selectedUser.set(user);
        this.form.reset({
            username: user.username,
            password: '',
            groups: user.groups.map(g => g.id),
            auto_start_tide_id: user.auto_start_tide_id ?? null,
            preferred_language: user.preferred_language ?? 'system'
        });
        this.form.controls.username.disable();
        this.form.controls.password.clearValidators();
        this.form.controls.password.updateValueAndValidity();
        this.displayDialog.set(true);
    }

    hideDialog(): void {
        this.displayDialog.set(false);
        this.selectedUser.set(null);
    }

    saveUser(): void {
        if (this.form.invalid) {
            this.form.markAllAsTouched();
            return;
        }

        const v = this.form.getRawValue();
        this.saving.set(true);

        const autoStartTideId = v.auto_start_tide_id || null;
        const obs = this.isNewUser()
            ? this.adminUserService.createUser({
                username: v.username!,
                password: v.password!,
                usertype: v.usertype ?? 'Internal',
                groups: v.groups ?? [],
                auto_start_tide_id: autoStartTideId,
                preferred_language: v.preferred_language!
            })
            : this.adminUserService.updateUser(this.selectedUser()!.id, {
                username: v.username!,
                groups: v.groups ?? [],
                auto_start_tide_id: autoStartTideId,
                preferred_language: v.preferred_language!
            });

        obs.subscribe({
            next: () => {
                this.messageService.add({
                    severity: 'success',
                    summary: this.translateService.instant('common.success'),
                    detail: this.translateService.instant(this.isNewUser() ? 'users.success.created' : 'users.success.updated')
                });
                this.hideDialog();
                this.loadUsers();
                this.saving.set(false);
            },
            error: (error: { error?: { error?: string } }) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translateService.instant('common.error'),
                    detail: error.error?.error ?? this.translateService.instant('users.errors.saveFailed')
                });
                this.saving.set(false);
            }
        });
    }

    deleteUser(user: TidalcaseUser): void {
        if (user.protected) return;
        this.confirmationService.confirm({
            message: this.translateService.instant('users.confirmDelete'),
            header: this.translateService.instant('common.confirmDelete'),
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: this.translateService.instant('yes'),
            rejectLabel: this.translateService.instant('no'),
            accept: () => {
                this.adminUserService.deleteUser(user.id).subscribe({
                    next: () => {
                        this.messageService.add({
                            severity: 'success',
                            summary: this.translateService.instant('common.success'),
                            detail: this.translateService.instant('users.success.deleted')
                        });
                        this.loadUsers();
                    },
                    error: (error: { error?: { error?: string } }) => {
                        this.messageService.add({
                            severity: 'error',
                            summary: this.translateService.instant('common.error'),
                            detail: error.error?.error ?? this.translateService.instant('users.errors.deleteFailed')
                        });
                    }
                });
            }
        });
    }

    getGroupNames(user: TidalcaseUser): string {
        return user.groups.map(g => g.display_name).join(', ') || '-';
    }
}
