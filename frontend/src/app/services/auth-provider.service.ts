import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface AuthProvider {
    _id?: string;
    name: string;
    slug?: string; // URL-safe identifier
    type: 'local' | 'ldap' | 'azure-ad' | 'oidc';
    priority: number;
    enabled: boolean;
    settings?: {
        ldap?: {
            servers?: string[];
            bindDN?: string;
            bindCredentials?: string;
            searchBase?: string;
            searchFilter?: string;
            usernameField?: string;
            emailField?: string;
            tlsRejectUnauthorized?: boolean;
            tlsCaCert?: string;
        };
        azureAd?: {
            clientID?: string;
            clientSecret?: string;
            tenantID?: string;
            callbackURL?: string;
        };
        oidc?: {
            issuerURL?: string;
            clientID?: string;
            clientSecret?: string;
            callbackURL?: string;
        };
    };
}

@Injectable({
    providedIn: 'root'
})
export class AuthProviderService {
    private readonly API_URL = "/api/auth/providers";

    constructor(private http: HttpClient) { }

    getEnabledProviders(): Observable<AuthProvider[]> {
        return this.http.get<AuthProvider[]>(`${this.API_URL}/enabled`);
    }

    getAllProviders(page = 0, limit = 0, sortField = 'priority', sortOrder = 1, filters: any = {}): Observable<{ data: AuthProvider[], totalRecords: number }> {
        let params: any = {
            page: page.toString(),
            limit: limit.toString(),
            sortField,
            sortOrder: sortOrder.toString()
        };

        Object.keys(filters).forEach(key => {
            params[`filters[${key}]`] = JSON.stringify(filters[key]);
        });

        return this.http.get<{ data: AuthProvider[], totalRecords: number }>(this.API_URL, { params });
    }

    createProvider(provider: AuthProvider): Observable<AuthProvider> {
        return this.http.post<AuthProvider>(this.API_URL, provider);
    }

    updateProvider(id: string, provider: Partial<AuthProvider>): Observable<AuthProvider> {
        return this.http.put<AuthProvider>(`${this.API_URL}/${id}`, provider);
    }

    deleteProvider(id: string): Observable<void> {
        return this.http.delete<void>(`${this.API_URL}/${id}`);
    }
}
