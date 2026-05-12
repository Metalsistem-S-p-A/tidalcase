import { ChangeDetectionStrategy, Component, computed, effect, inject, signal, viewChild } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormArray, FormBuilder, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { ConfirmationService, FilterMetadata, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputTextModule } from 'primeng/inputtext';
import { MenuModule } from 'primeng/menu';
import { MessageModule } from 'primeng/message';
import { MultiSelectModule } from 'primeng/multiselect';
import { PasswordModule } from 'primeng/password';
import { SelectModule } from 'primeng/select';
import { Table, TableLazyLoadEvent, TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { TextareaModule } from 'primeng/textarea';
import { ToggleSwitchModule } from 'primeng/toggleswitch';
import { AuthProvider, AuthProviderService } from '../../../services/auth-provider.service';


@Component({
    selector: 'app-auth-providers',
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [
        FormsModule,
        ReactiveFormsModule,
        TranslateModule,
        TableModule,
        ButtonModule,
        DialogModule,
        InputTextModule,
        ToggleSwitchModule,
        SelectModule,
        InputNumberModule,
        PasswordModule,
        MessageModule,
        MenuModule,
        ConfirmDialogModule,
        TextareaModule,
        InputIconModule,
        IconFieldModule,
        MultiSelectModule,
        TagModule
    ],
    templateUrl: './auth-providers.html'
})
export class AuthProvidersComponent {
    private readonly translateService = inject(TranslateService);
    private readonly authProviderService = inject(AuthProviderService);
    private readonly confirmationService = inject(ConfirmationService);
    private readonly messageService = inject(MessageService);
    private readonly fb = inject(FormBuilder);

    readonly table = viewChild<Table>('dt');

    readonly providers = signal<AuthProvider[]>([]);
    readonly totalRecords = signal(0);
    readonly displayDialog = signal(false);
    readonly selectedProvider = signal<AuthProvider | null>(null);
    readonly isNewProvider = signal(false);
    readonly loading = signal(false);

    readonly providerTypes = [
        { label: 'Local', value: 'local' },
        { label: 'LDAP', value: 'ldap' },
        { label: 'Azure AD', value: 'azure-ad' },
        { label: 'OIDC', value: 'oidc' }
    ];

    readonly createProviderMenuItems = [
        { label: 'LDAP', icon: 'pi pi-shield', command: () => this.showCreateDialog('ldap') },
        { label: 'Azure AD', icon: 'pi pi-microsoft', command: () => this.showCreateDialog('azure-ad') },
        { label: 'OIDC', icon: 'pi pi-id-card', command: () => this.showCreateDialog('oidc') }
    ];

    readonly form = this.fb.group({
        name: [''],
        type: ['local' as AuthProvider['type']],
        priority: [0],
        enabled: [true],
        ldapServers: this.fb.array([this.fb.control('')]),
        ldapBindDN: [''],
        ldapBindCredentials: [''],
        ldapSearchBase: [''],
        ldapSearchFilter: ['(uid={{username}})'],
        ldapUsernameField: ['uid'],
        ldapEmailField: [''],
        ldapTlsRejectUnauthorized: [true],
        ldapTlsCaCert: [''],
        azureTenantID: [''],
        azureClientID: [''],
        azureClientSecret: [''],
        azureCallbackURL: [''],
        oidcIssuerURL: [''],
        oidcClientID: [''],
        oidcClientSecret: [''],
        oidcCallbackURL: [''],
    });

    private readonly currentName = toSignal(this.form.controls.name.valueChanges, { initialValue: '' });
    readonly currentType = toSignal(this.form.controls.type.valueChanges, { initialValue: 'local' as AuthProvider['type'] });
    readonly tlsRejectUnauthorized = toSignal(this.form.controls.ldapTlsRejectUnauthorized.valueChanges, { initialValue: true });

    private readonly doc = inject(DOCUMENT);

    readonly computedSlug = computed(() => {
        const name = this.currentName() ?? '';
        return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
    });

    readonly computedOidcCallbackURL = computed(() => {
        const slug = this.computedSlug();
        if (!slug || this.currentType() !== 'oidc') return '';
        return `${this.doc.location.origin}/api/auth/oidc/${slug}/callback`;
    });

    constructor() {
        effect(() => {
            const url = this.computedOidcCallbackURL();
            this.form.controls.oidcCallbackURL.setValue(url, { emitEvent: false });
        });
    }

    get ldapServers(): FormArray {
        return this.form.controls.ldapServers;
    }

    onLazyLoad(event: TableLazyLoadEvent): void {
        this.loading.set(true);
        const first = event.first ?? 0;
        const rows = event.rows ?? 50;
        this.authProviderService.getAllProviders(
            first / rows,
            rows,
            (Array.isArray(event.sortField) ? event.sortField[0] : event.sortField) ?? 'priority',
            event.sortOrder ?? 1,
            this.buildFilters(event.filters)
        ).subscribe({
            next: (response) => {
                this.providers.set(response.data);
                this.totalRecords.set(response.totalRecords);
                this.loading.set(false);
            },
            error: () => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translateService.instant('common.error'),
                    detail: this.translateService.instant('authProviders.errors.loadFailed')
                });
                this.loading.set(false);
            }
        });
    }

    private buildFilters(rawFilters?: TableLazyLoadEvent['filters']): Record<string, unknown> {
        if (!rawFilters) return {};
        const result: Record<string, unknown> = {};
        for (const [field, filterData] of Object.entries(rawFilters)) {
            if (!filterData) continue;
            if (Array.isArray(filterData)) {
                const constraints = filterData
                    .filter((f: FilterMetadata) => f.value !== null && f.value !== undefined && f.value !== '')
                    .map((f: FilterMetadata) => ({ value: f.value, matchMode: f.matchMode ?? 'contains' }));
                if (constraints.length > 0) {
                    result[field] = { operator: (filterData[0] as FilterMetadata)?.operator ?? 'and', constraints };
                }
            } else if (filterData.value !== null && filterData.value !== undefined && filterData.value !== '') {
                result[field] = {
                    operator: filterData.operator ?? 'and',
                    constraints: [{ value: filterData.value, matchMode: filterData.matchMode ?? 'contains' }]
                };
            }
        }
        return result;
    }

    showCreateDialog(providerType: 'ldap' | 'azure-ad' | 'oidc'): void {
        this.isNewProvider.set(true);
        this.selectedProvider.set(null);
        this.resetLdapServers(['']);
        this.form.patchValue({
            name: '',
            type: providerType,
            enabled: true,
            priority: 0,
            ldapBindDN: '',
            ldapBindCredentials: '',
            ldapSearchBase: '',
            ldapSearchFilter: '(uid={{username}})',
            ldapUsernameField: 'uid',
            ldapEmailField: '',
            ldapTlsRejectUnauthorized: true,
            ldapTlsCaCert: '',
            azureTenantID: '',
            azureClientID: '',
            azureClientSecret: '',
            azureCallbackURL: '',
            oidcIssuerURL: '',
            oidcClientID: '',
            oidcClientSecret: '',
            oidcCallbackURL: '',
        });
        this.displayDialog.set(true);
    }

    showEditDialog(provider: AuthProvider): void {
        this.isNewProvider.set(false);
        this.selectedProvider.set(provider);
        this.resetLdapServers(provider.settings?.ldap?.servers?.length ? provider.settings.ldap.servers : ['']);
        this.form.patchValue({
            name: provider.name,
            type: provider.type,
            enabled: provider.enabled,
            priority: provider.priority ?? 0,
            ldapBindDN: provider.settings?.ldap?.bindDN ?? '',
            ldapBindCredentials: provider.settings?.ldap?.bindCredentials ?? '',
            ldapSearchBase: provider.settings?.ldap?.searchBase ?? '',
            ldapSearchFilter: provider.settings?.ldap?.searchFilter ?? '(uid={{username}})',
            ldapUsernameField: provider.settings?.ldap?.usernameField ?? 'uid',
            ldapEmailField: provider.settings?.ldap?.emailField ?? '',
            ldapTlsRejectUnauthorized: provider.settings?.ldap?.tlsRejectUnauthorized ?? true,
            ldapTlsCaCert: provider.settings?.ldap?.tlsCaCert ?? '',
            azureTenantID: provider.settings?.azureAd?.tenantID ?? '',
            azureClientID: provider.settings?.azureAd?.clientID ?? '',
            azureClientSecret: provider.settings?.azureAd?.clientSecret ?? '',
            azureCallbackURL: provider.settings?.azureAd?.callbackURL ?? '',
            oidcIssuerURL: provider.settings?.oidc?.issuerURL ?? '',
            oidcClientID: provider.settings?.oidc?.clientID ?? '',
            oidcClientSecret: provider.settings?.oidc?.clientSecret ?? '',
            oidcCallbackURL: provider.settings?.oidc?.callbackURL ?? '',
        });
        this.displayDialog.set(true);
    }

    hideDialog(): void {
        this.displayDialog.set(false);
        this.selectedProvider.set(null);
    }

    saveProvider(): void {
        const v = this.form.getRawValue();
        if (!v.name || !v.type) {
            this.messageService.add({
                severity: 'warn',
                summary: this.translateService.instant('common.warning'),
                detail: this.translateService.instant('authProviders.errors.missingRequiredFields')
            });
            return;
        }

        this.loading.set(true);
        const isNew = this.isNewProvider();
        const provider = this.selectedProvider();
        const payload: Partial<AuthProvider> = {
            name: v.name,
            type: v.type,
            enabled: v.enabled ?? true,
            priority: v.priority ?? 0,
            settings: {
                ldap: {
                    servers: (v.ldapServers as string[]).filter(Boolean),
                    bindDN: v.ldapBindDN ?? '',
                    bindCredentials: v.ldapBindCredentials ?? '',
                    searchBase: v.ldapSearchBase ?? '',
                    searchFilter: v.ldapSearchFilter ?? '',
                    usernameField: v.ldapUsernameField ?? '',
                    emailField: v.ldapEmailField ?? '',
                    tlsRejectUnauthorized: v.ldapTlsRejectUnauthorized ?? true,
                    tlsCaCert: v.ldapTlsCaCert ?? '',
                },
                azureAd: {
                    tenantID: v.azureTenantID ?? '',
                    clientID: v.azureClientID ?? '',
                    clientSecret: v.azureClientSecret ?? '',
                    callbackURL: v.azureCallbackURL ?? '',
                },
                oidc: {
                    issuerURL: v.oidcIssuerURL ?? '',
                    clientID: v.oidcClientID ?? '',
                    clientSecret: v.oidcClientSecret ?? '',
                    callbackURL: v.oidcCallbackURL ?? '',
                }
            }
        };

        const obs = isNew
            ? this.authProviderService.createProvider(payload as AuthProvider)
            : this.authProviderService.updateProvider(provider!._id!, payload);

        obs.subscribe({
            next: () => {
                this.messageService.add({
                    severity: 'success',
                    summary: this.translateService.instant('common.success'),
                    detail: this.translateService.instant(isNew ? 'authProviders.success.created' : 'authProviders.success.updated')
                });
                this.reloadTableData();
                this.hideDialog();
                this.loading.set(false);
            },
            error: (error: { error?: { message?: string } }) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translateService.instant('common.error'),
                    detail: error.error?.message ?? this.translateService.instant(isNew ? 'authProviders.errors.creationFailed' : 'authProviders.errors.updateFailed')
                });
                this.loading.set(false);
            }
        });
    }

    deleteProvider(provider: AuthProvider): void {
        this.confirmationService.confirm({
            message: this.translateService.instant('authProviders.confirmDelete', { name: provider.name }),
            header: this.translateService.instant('common.confirmDelete'),
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: this.translateService.instant('yes'),
            rejectLabel: this.translateService.instant('no'),
            accept: () => {
                this.authProviderService.deleteProvider(provider._id!).subscribe({
                    next: () => {
                        this.messageService.add({
                            severity: 'success',
                            summary: this.translateService.instant('common.success'),
                            detail: this.translateService.instant('authProviders.success.deleted')
                        });
                        this.reloadTableData();
                    },
                    error: (error: { error?: { message?: string } }) => {
                        this.messageService.add({
                            severity: 'error',
                            summary: this.translateService.instant('common.error'),
                            detail: error.error?.message ?? this.translateService.instant('authProviders.errors.deleteFailed')
                        });
                    }
                });
            }
        });
    }

    getProviderTypeLabel(type: string): string {
        return this.providerTypes.find(pt => pt.value === type)?.label ?? type;
    }

    addLdapServer(): void {
        this.ldapServers.push(this.fb.control(''));
    }

    removeLdapServer(index: number): void {
        if (this.ldapServers.length > 1) {
            this.ldapServers.removeAt(index);
        }
    }

    private resetLdapServers(servers: string[]): void {
        while (this.ldapServers.length > 0) {
            this.ldapServers.removeAt(0);
        }
        servers.forEach(s => this.ldapServers.push(this.fb.control(s)));
    }

    reloadTableData(): void {
        const t = this.table();
        if (t) {
            this.onLazyLoad(t.createLazyLoadMetadata());
        }
    }
}
