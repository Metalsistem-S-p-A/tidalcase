import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { CheckboxModule } from 'primeng/checkbox';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { MultiSelectModule } from 'primeng/multiselect';
import { PasswordModule } from 'primeng/password';
import { SelectModule } from 'primeng/select';
import { TableModule } from 'primeng/table';
import { TabsModule } from 'primeng/tabs';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { AuthService } from '../../services/auth.service';
import { UserService } from '../../services/user.service';
import { Tide, TideService } from '@/app/services/tide.service';

@Component({
    selector: 'app-profile',
    imports: [
        CommonModule,
        FormsModule,
        TranslateModule,
        CardModule,
        InputTextModule,
        PasswordModule,
        ButtonModule,
        MessageModule,
        DialogModule,
        CheckboxModule,
        SelectModule,
        TabsModule,
        TooltipModule,
        TableModule,
        InputNumberModule,
        MultiSelectModule,
        TagModule,
        ConfirmDialogModule,
    ],
    templateUrl: './profile.html',
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProfileComponent implements OnInit {
    readonly currentPassword = signal('');
    readonly newPassword = signal('');
    readonly confirmPassword = signal('');
    readonly email = signal('');
    readonly isLoading = signal(false);
    readonly isLoadingEmail = signal(false);

    readonly mfaEnabled = signal(false);
    readonly mfaSetupDialog = signal(false);
    readonly mfaDisableDialog = signal(false);
    readonly mfaQrCode = signal('');
    readonly mfaSecret = signal('');
    readonly mfaToken = signal('');
    readonly mfaPassword = signal('');
    readonly isLoadingMfa = signal(false);
    readonly mfaTrustDuration = signal(30);
    readonly isLoadingMfaTrust = signal(false);
    readonly showTrustedDevicesDialog = signal(false);
    readonly trustedDevices = signal<any[]>([]);
    readonly availableTides = signal<{ label: string; value: string }[]>([]);

    readonly notificationEvents = signal<string[]>([]);

    readonly authService = inject(AuthService);
    private readonly userService = inject(UserService);
    private readonly messageService = inject(MessageService);
    readonly translateService = inject(TranslateService);
    private readonly confirmationService = inject(ConfirmationService);
    private readonly tideService = inject(TideService);

    autostartTide = signal('');

    readonly currentUser = computed(() => this.authService.currentUser());
    readonly isLocalUser = computed(() => this.currentUser()?.authProvider === 'local');
    readonly isLocalOrLdapUser = computed(() => {
        const provider = this.currentUser()?.authProvider;
        return provider === 'local' || provider === 'ldap';
    });

    ngOnInit() {
        this.loadUserData();
        this.loadTides();
    }

    private loadTides(): void {
            this.tideService.getTides().subscribe({
                next: (res: { success: boolean; tides: Tide[] }) => {
                    const none = { label: this.translateService.instant('users.autoStartTideNone'), value: '' };
                    const tides = (res.tides || []).map((t: Tide) => ({ label: t.display_name, value: t.id }));
                    this.availableTides.set([none, ...tides]);
                },
                error: () => {}
            });
        }

    loadUserData(): void {
        this.userService.getCurrentUser().subscribe({
            next: (user: any) => {
                this.email.set(user.email || '');
                this.mfaEnabled.set(user.mfaEnabled || false);
                this.mfaTrustDuration.set(user.mfaTrustDuration || 30);
                this.notificationEvents.set(user.notificationEvents || []);
                this.autostartTide.set(user.autostartTideId || '');
            },
            error: () => {}
        });
    }

    updateAutostartTide() : void {
        this.userService.updateAutostartTide(this.autostartTide()).subscribe({
            next: () => {
                this.messageService.add({
                    severity: 'success',
                    summary: this.translateService.instant('common.success'),
                    detail: this.translateService.instant('users.success.updated')
                });
            },
            error: (error: any) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translateService.instant('common.error'),
                    detail: error.error?.message || this.translateService.instant('users.errors.saveFailed')
                });
            }
        });
    }

    updateEmail(): void {
        if (!this.email()) {
            this.messageService.add({
                severity: 'error',
                summary: this.translateService.instant('common.error'),
                detail: this.translateService.instant('auth.errors.emailRequired')
            });
            return;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(this.email())) {
            this.messageService.add({
                severity: 'error',
                summary: this.translateService.instant('common.error'),
                detail: this.translateService.instant('auth.errors.invalidEmailFormat')
            });
            return;
        }

        this.isLoadingEmail.set(true);
        this.userService.updateEmail(this.email()).subscribe({
            next: () => {
                this.messageService.add({
                    severity: 'success',
                    summary: this.translateService.instant('common.success'),
                    detail: this.translateService.instant('auth.success.emailUpdated')
                });
                this.isLoadingEmail.set(false);
            },
            error: (error: any) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translateService.instant('common.error'),
                    detail: error.error?.message || this.translateService.instant('auth.errors.emailUpdateFailed')
                });
                this.isLoadingEmail.set(false);
            }
        });
    }

    changePassword(): void {
        if (!this.currentPassword() || !this.newPassword() || !this.confirmPassword()) {
            this.messageService.add({
                severity: 'error',
                summary: this.translateService.instant('common.error'),
                detail: this.translateService.instant('auth.errors.allFieldsRequired')
            });
            return;
        }

        if (this.newPassword() !== this.confirmPassword()) {
            this.messageService.add({
                severity: 'error',
                summary: this.translateService.instant('common.error'),
                detail: this.translateService.instant('auth.errors.passwordsDoNotMatch')
            });
            return;
        }

        if (this.newPassword().length < 6) {
            this.messageService.add({
                severity: 'error',
                summary: this.translateService.instant('common.error'),
                detail: this.translateService.instant('auth.errors.passwordTooShort')
            });
            return;
        }

        this.isLoading.set(true);
        this.userService.changePassword(this.currentPassword(), this.newPassword()).subscribe({
            next: () => {
                this.messageService.add({
                    severity: 'success',
                    summary: this.translateService.instant('common.success'),
                    detail: this.translateService.instant('auth.passwordChangedSuccessfully')
                });
                this.currentPassword.set('');
                this.newPassword.set('');
                this.confirmPassword.set('');
                this.isLoading.set(false);
            },
            error: (error: any) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translateService.instant('common.error'),
                    detail: error.error?.message || this.translateService.instant('auth.errors.passwordChangeFailed')
                });
                this.isLoading.set(false);
            }
        });
    }

    startMfaSetup(): void {
        this.isLoadingMfa.set(true);
        this.userService.setupMFA().subscribe({
            next: (response: any) => {
                this.mfaQrCode.set(response.qrCode);
                this.mfaSecret.set(response.secret);
                this.mfaSetupDialog.set(true);
                this.isLoadingMfa.set(false);
            },
            error: (error: any) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translateService.instant('common.error'),
                    detail: error.error?.message || this.translateService.instant('mfa.errors.failed')
                });
                this.isLoadingMfa.set(false);
            }
        });
    }

    verifyAndEnableMfa(): void {
        if (!this.mfaToken() || this.mfaToken().length !== 6) {
            this.messageService.add({
                severity: 'error',
                summary: this.translateService.instant('common.error'),
                detail: this.translateService.instant('mfa.errors.invalid')
            });
            return;
        }

        this.isLoadingMfa.set(true);
        this.userService.verifyAndEnableMFA(this.mfaToken()).subscribe({
            next: () => {
                this.messageService.add({
                    severity: 'success',
                    summary: this.translateService.instant('common.success'),
                    detail: this.translateService.instant('mfa.success.enabled')
                });
                this.mfaEnabled.set(true);
                this.mfaSetupDialog.set(false);
                this.mfaToken.set('');
                this.mfaQrCode.set('');
                this.mfaSecret.set('');
                this.isLoadingMfa.set(false);
            },
            error: (error: any) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translateService.instant('common.error'),
                    detail: error.error?.message || this.translateService.instant('mfa.errors.failed')
                });
                this.isLoadingMfa.set(false);
            }
        });
    }

    openDisableMfaDialog(): void {
        this.mfaDisableDialog.set(true);
        this.mfaPassword.set('');
        this.mfaToken.set('');
    }

    disableMfa(): void {
        if (this.isLocalUser() && !this.mfaPassword()) {
            this.messageService.add({
                severity: 'error',
                summary: this.translateService.instant('common.error'),
                detail: this.translateService.instant('mfa.errors.passwordRequired')
            });
            return;
        }

        if (!this.mfaToken() || this.mfaToken().length !== 6) {
            this.messageService.add({
                severity: 'error',
                summary: this.translateService.instant('common.error'),
                detail: this.translateService.instant('mfa.errors.invalid')
            });
            return;
        }

        this.isLoadingMfa.set(true);
        this.userService.disableMFA(this.mfaPassword(), this.mfaToken()).subscribe({
            next: () => {
                this.messageService.add({
                    severity: 'success',
                    summary: this.translateService.instant('common.success'),
                    detail: this.translateService.instant('mfa.success.disabled')
                });
                this.mfaEnabled.set(false);
                this.mfaDisableDialog.set(false);
                this.mfaPassword.set('');
                this.mfaToken.set('');
                this.isLoadingMfa.set(false);
            },
            error: (error: any) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translateService.instant('common.error'),
                    detail: error.error?.message || this.translateService.instant('mfa.errors.disableFailed')
                });
                this.isLoadingMfa.set(false);
            }
        });
    }

    cancelMfaSetup(): void {
        this.mfaSetupDialog.set(false);
        this.mfaToken.set('');
        this.mfaQrCode.set('');
        this.mfaSecret.set('');
    }

    cancelMfaDisable(): void {
        this.mfaDisableDialog.set(false);
        this.mfaPassword.set('');
        this.mfaToken.set('');
    }

    updateMfaTrustDuration(): void {
        if (this.mfaTrustDuration() < 0 || this.mfaTrustDuration() > 365) {
            this.messageService.add({
                severity: 'error',
                summary: this.translateService.instant('common.error'),
                detail: this.translateService.instant('mfa.errors.invalidTrustDuration')
            });
            return;
        }

        this.isLoadingMfaTrust.set(true);
        this.userService.updateMfaTrustDuration(this.mfaTrustDuration()).subscribe({
            next: () => {
                this.messageService.add({
                    severity: 'success',
                    summary: this.translateService.instant('common.success'),
                    detail: this.translateService.instant('mfa.success.trustDurationUpdated')
                });
                this.isLoadingMfaTrust.set(false);
            },
            error: () => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translateService.instant('common.error'),
                    detail: this.translateService.instant('profile.errors.updateFailed')
                });
                this.isLoadingMfaTrust.set(false);
            }
        });
    }

    loadTrustedDevices(): void {
        this.userService.getTrustedDevices().subscribe({
            next: (devices) => {
                this.trustedDevices.set(devices);
                this.showTrustedDevicesDialog.set(true);
            },
            error: () => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.translateService.instant('common.error'),
                    detail: this.translateService.instant('mfa.errors.loadTrustedDevicesFailed')
                });
            }
        });
    }

    revokeTrustedDevice(deviceId: string): void {
        this.confirmationService.confirm({
            message: this.translateService.instant('mfa.confirmRevoke'),
            header: this.translateService.instant('common.confirm'),
            icon: 'pi pi-exclamation-triangle',
            accept: () => {
                this.userService.revokeTrustedDevice(deviceId).subscribe({
                    next: () => {
                        this.messageService.add({
                            severity: 'success',
                            summary: this.translateService.instant('common.success'),
                            detail: this.translateService.instant('mfa.success.revoked')
                        });
                        this.loadTrustedDevices();
                    },
                    error: () => {
                        this.messageService.add({
                            severity: 'error',
                            summary: this.translateService.instant('common.error'),
                            detail: this.translateService.instant('mfa.errors.revokeFailed')
                        });
                    }
                });
            }
        });
    }

    revokeAllTrustedDevices(): void {
        this.confirmationService.confirm({
            message: this.translateService.instant('mfa.confirmRevokeAll'),
            header: this.translateService.instant('common.confirm'),
            icon: 'pi pi-exclamation-triangle',
            accept: () => {
                this.userService.revokeAllTrustedDevices().subscribe({
                    next: () => {
                        this.messageService.add({
                            severity: 'success',
                            summary: this.translateService.instant('common.success'),
                            detail: this.translateService.instant('mfa.success.revokedAll')
                        });
                        this.trustedDevices.set([]);
                        this.showTrustedDevicesDialog.set(false);
                    },
                    error: () => {
                        this.messageService.add({
                            severity: 'error',
                            summary: this.translateService.instant('common.error'),
                            detail: this.translateService.instant('mfa.errors.revokeFailed')
                        });
                    }
                });
            }
        });
    }
}
