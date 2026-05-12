import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface Registry {
    id?: string | number;
    url: string;
    info?: { name?: string; [key: string]: any };
    tides?: any[];
}

@Injectable({ providedIn: 'root' })
export class RegistryService {
    private http = inject(HttpClient);

    getRegistries(): Observable<{ success: boolean; registry: Registry[]; registry_locked: boolean; tidalcase_version: string }> {
        return this.http.get<any>('/api/admin/registry');
    }

    addRegistry(url: string): Observable<{ success: boolean; error?: string }> {
        return this.http.post<any>('/api/admin/registry', { url });
    }

    deleteRegistry(id: string | number): Observable<{ success: boolean; error?: string }> {
        return this.http.delete<any>('/api/admin/registry', { body: { id } });
    }
}
