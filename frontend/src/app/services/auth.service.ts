import { HttpClient } from '@angular/common/http';
import { Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, map, of, tap } from 'rxjs';

export interface LoginRequest {
    username: string;
    password: string;
    provider?: string;
    deviceId?: string;
    remember_me?: boolean;
}

export interface LoginResponse {
    token?: string;
    requiresMfa?: boolean;
    tempUserId?: string;
    username?: string;
    deviceId?: string;
    user?: CurrentUser;
}

export interface CurrentUser {
    id: string;
    username: string;
    authProvider: 'local' | 'ldap' | 'azure-ad' | 'oidc';
    authProviderName?: string;
    isAdmin: boolean;
    permissions?: Record<string, string>;
    settings: Record<string, any>;
}

interface MeResponse {
    user: CurrentUser;
}

@Injectable({
    providedIn: 'root'
})
export class AuthService {
    private readonly TOKEN_KEY = 'auth_token';

    isAuthenticated = signal<boolean>(this.isTokenValid());
    currentUser = signal<CurrentUser | null>(null);

    constructor(private http: HttpClient, private router: Router) {
        if (this.isTokenValid()) {
            this.loadUserFromToken();
        } else {
            this.removeToken();
        }
    }

    login(credentials: LoginRequest): Observable<LoginResponse> {
        return this.http.post<LoginResponse>('/api/auth/login', credentials).pipe(
            tap(response => {
                if (!response.requiresMfa && response.token && response.user) {
                    this.setToken(response.token);
                    this.currentUser.set(response.user);
                    this.isAuthenticated.set(true);
                }
            })
        );
    }

    verifyMfaToken(tempUserId: string, token: string, trustDevice: boolean = false, deviceId?: string): Observable<LoginResponse> {
        return this.http.post<LoginResponse>('/api/auth/verify-mfa', {
            tempUserId,
            token,
            trustDevice,
            deviceId
        }).pipe(
            tap(response => {
                if (response.token && response.user) {
                    this.setToken(response.token);
                    this.currentUser.set(response.user);
                    this.isAuthenticated.set(true);
                }
            })
        );
    }

    tryMe(): Observable<boolean> {
        return this.http.get<MeResponse>('/api/auth/me').pipe(
            tap(response => {
                this.currentUser.set(response.user);
                this.isAuthenticated.set(true);
            }),
            map(() => true),
            catchError(() => of(false))
        );
    }

    tryRefresh(): Observable<boolean> {
        return this.http.post<LoginResponse>('/api/auth/refresh', {}).pipe(
            tap(response => {
                if (response.token && response.user) {
                    this.setToken(response.token);
                    this.currentUser.set(response.user);
                    this.isAuthenticated.set(true);
                }
            }),
            map(() => true),
            catchError(() => of(false))
        );
    }

    logout(): void {
        this.http.post('/api/auth/logout', {}).pipe(catchError(() => of(null))).subscribe();
        this.removeToken();
        sessionStorage.removeItem('auto_start_done');
        this.currentUser.set(null);
        this.isAuthenticated.set(false);
        this.router.navigateByUrl('/auth/login', { replaceUrl: true });
    }

    storeToken(token: string): void {
        localStorage.setItem(this.TOKEN_KEY, token);
        if (this.isTokenValid()) {
            this.loadUserFromToken();
            this.isAuthenticated.set(true);
        }
    }

    isAdmin(): boolean {
        return this.currentUser()?.isAdmin === true;
    }

    hasPermission(resource: string, level: 'read' | 'write'): boolean {
        const user = this.currentUser();
        if (!user) return false;
        if (user.isAdmin) return true;
        const levelOrder: Record<string, number> = { none: 0, read: 1, write: 2 };
        const userLevel = user.permissions?.[resource] || 'none';
        return (levelOrder[userLevel] ?? 0) >= (levelOrder[level] ?? 1);
    }

    isReadOnly(): boolean {
        return !this.isAdmin() && !this.hasPermission('certificates', 'write');
    }

    updateLanguage(lang: string): Observable<void> {
        return this.http.patch<{ success: boolean }>('/api/user/language', { language: lang }).pipe(
            tap(() => {
                const user = this.currentUser();
                if (user) {
                    this.currentUser.set({
                        ...user,
                        settings: { ...user.settings, preferred_language: lang }
                    });
                }
            }),
            map(() => undefined)
        );
    }

    private getToken(): string | null {
        return localStorage.getItem(this.TOKEN_KEY);
    }

    private setToken(token: string): void {
        localStorage.setItem(this.TOKEN_KEY, token);
    }

    private removeToken(): void {
        localStorage.removeItem(this.TOKEN_KEY);
    }

    private isTokenValid(): boolean {
        const token = this.getToken();
        if (!token) return false;
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            if (payload.exp) {
                return payload.exp > Math.floor(Date.now() / 1000);
            }
            return true;
        } catch {
            return false;
        }
    }

    private loadUserFromToken(): void {
        const token = this.getToken();
        if (!token) return;
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            if (payload.exp && payload.exp <= Math.floor(Date.now() / 1000)) {
                this.logout();
                return;
            }
            this.currentUser.set({
                id: payload.userId,
                username: payload.username,
                authProvider: payload.authProvider,
                authProviderName: payload.authProviderName,
                isAdmin: payload.isAdmin === true,
                permissions: payload.permissions,
                settings: payload.settings,
            });
        } catch {
            this.logout();
        }
    }
}
