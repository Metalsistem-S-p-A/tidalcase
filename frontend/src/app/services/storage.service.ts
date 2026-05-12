import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface StorageProvider {
    id?: string;
    display_name: string;
    enabled: boolean;
    provider_type: string;
    default_destination: string;
    volume_config: Record<string, unknown>;
    created_at?: string;
}

export interface StorageMount {
    id?: string;
    storage_provider_id: string;
    provider_display_name?: string;
    enabled: boolean;
    read_only: boolean;
    destination: string;
}

@Injectable({ providedIn: 'root' })
export class StorageService {
    private http = inject(HttpClient);

    getProviders(): Observable<{ success: boolean; providers: StorageProvider[] }> {
        return this.http.get<any>('/api/admin/storage-providers');
    }

    saveProvider(p: Partial<StorageProvider>): Observable<{ success: boolean; id?: string; error?: string }> {
        return this.http.post<any>('/api/admin/storage-provider', p);
    }

    deleteProvider(id: string): Observable<{ success: boolean; error?: string }> {
        return this.http.delete<any>('/api/admin/storage-provider', { body: { id } });
    }

    getMounts(tideId: string): Observable<{ success: boolean; mounts: StorageMount[] }> {
        return this.http.get<any>(`/api/admin/tide/${tideId}/storage-mounts`);
    }

    saveMounts(tideId: string, mounts: StorageMount[]): Observable<{ success: boolean; error?: string }> {
        return this.http.post<any>(`/api/admin/tide/${tideId}/storage-mounts`, { mounts });
    }
}
