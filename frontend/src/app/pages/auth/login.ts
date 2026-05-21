import { CommonModule } from '@angular/common';
import { Component, inject, model, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TranslateDirective, TranslateModule, TranslatePipe, TranslateService } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { RippleModule } from 'primeng/ripple';
import { AppTopbar } from '../../layout/component/app.topbar';
import { AuthProvider, AuthProviderService } from '../../services/auth-provider.service';
import { AuthService } from '@/app/services/auth.service';

@Component({
    selector: 'app-login',
    standalone: true,
    imports: [CommonModule, ButtonModule, AppTopbar, CheckboxModule, InputTextModule, PasswordModule, FormsModule, RouterModule, RippleModule, TranslateDirective, TranslatePipe, TranslateModule, DialogModule],
    templateUrl: './login.html'
})
export class Login implements OnInit {
    private authService = inject(AuthService);
    private authProviderService = inject(AuthProviderService);
    private router = inject(Router);
    private route = inject(ActivatedRoute);
    private translate = inject(TranslateService);

    username: string = '';
    password: string = '';
    checked: boolean = false;
    isLoading: boolean = false;
    errorMessage: string = '';
    sessionExpiredMessage: string = '';

    // MFA properties
    showMfaDialog: boolean = false;
    mfaToken: string = '';
    tempUserId: string = '';
    mfaUsername: string = '';
    trustDevice: boolean = false;
    deviceId: string = '';

    // Separate direct and external providers
    directProviders = model<AuthProvider[]>([]); // local, ldap
    externalProviders = model<AuthProvider[]>([]); // oauth2, azure-ad

    ngOnInit(): void {
        // Load device ID from localStorage
        this.deviceId = localStorage.getItem('mfa_device_id') || '';

        // Check for session expiration
        this.route.queryParams.subscribe(params => {
            if (params['expired'] === 'true') {
                this.sessionExpiredMessage = this.translate.instant('auth.sessionExpired');
            }

            // Check for token from OAuth/Azure redirect
            if (params['token']) {

                // Store token in localStorage with correct key (same as AuthService)
                localStorage.setItem('auth_token', params['token']);

                // Decode token to set user info
                try {
                    const payload = JSON.parse(atob(params['token'].split('.')[1]));
                    this.authService.currentUser.set({
                        id: payload.userId,
                        username: payload.username,
                        authProvider: payload.authProvider || 'local',
                        authProviderName: payload.authProviderName,
                        isAdmin: payload.isAdmin === true,
                        permissions: payload.permissions,
                        settings: payload.settings
                    });
                    this.authService.isAuthenticated.set(true);
                } catch (error) {
                }

                // Navigate without returnUrl to avoid redirect loop
                this.router.navigate(['/'], { replaceUrl: true });
            } else if (params['error']) {
                this.errorMessage = this.translate.instant('auth.errors.loginFailed');
            }
        });

        this.loadAuthProviders();
    }

    loadAuthProviders(): void {
        this.authProviderService.getEnabledProviders().subscribe({
            next: (providers) => {
                // Separate direct from external providers
                this.directProviders.set( providers
                    .filter(p => p.type === 'local' || p.type === 'ldap')
                    .sort((a, b) => a.priority - b.priority));

                this.externalProviders.set(providers
                    .filter(p => p.type === 'azure-ad' || p.type === 'oidc')
                    .sort((a, b) => a.priority - b.priority));
            },
            error: (error) => {
            }
        });
    }

    onLogin(): void {
        if (!this.username || !this.password) {
            this.errorMessage = this.translate.instant('auth.errors.required');
            return;
        }

        this.isLoading = true;
        this.errorMessage = '';

        this.authService.login({
            username: this.username,
            password: this.password,
            deviceId: this.deviceId,
            remember_me: this.checked,
        }).subscribe({
            next: (response) => {
                // Check if MFA is required
                if (response.requiresMfa && response.tempUserId) {
                    this.tempUserId = response.tempUserId;
                    this.mfaUsername = response.username || this.username;
                    this.showMfaDialog = true;
                    this.isLoading = false;
                } else {
                    // Normal login or trusted device
                    if (response.deviceId) {
                        localStorage.setItem('mfa_device_id', response.deviceId);
                    }
                    const returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/';
                    this.router.navigateByUrl(returnUrl, { replaceUrl: true });
                }
            },
            error: (error) => {
                this.errorMessage = this.translate.instant(error.error?.message || 'loginFailed');
                this.isLoading = false;
            }
        });
    }

    verifyMfa(): void {
        if (!this.mfaToken || this.mfaToken.length !== 6) {
            this.errorMessage = this.translate.instant('mfa.errors.invalid');
            return;
        }

        this.isLoading = true;
        this.errorMessage = '';

        this.authService.verifyMfaToken(
            this.tempUserId,
            this.mfaToken,
            this.trustDevice,
            this.deviceId
        ).subscribe({
            next: (response) => {
                if (response.deviceId) {
                    localStorage.setItem('mfa_device_id', response.deviceId);
                }
                const returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/';
                this.router.navigateByUrl(returnUrl, { replaceUrl: true });
            },
            error: (error) => {
                this.errorMessage = this.translate.instant(error.error?.message || 'mfaVerificationFailed');
                this.isLoading = false;
            }
        });
    }

    cancelMfa(): void {
        this.showMfaDialog = false;
        this.mfaToken = '';
        this.tempUserId = '';
        this.trustDevice = false;
        this.isLoading = false;
    }

    onExternalProviderLogin(provider: AuthProvider): void {
        if (!provider.slug) return;
        if (provider.type === 'oidc') {
            window.location.href = `/api/auth/oidc/${provider.slug}/login`;
        } else {
            window.location.href = `/auth/${provider.type}/${provider.slug}`;
        }
    }
}
