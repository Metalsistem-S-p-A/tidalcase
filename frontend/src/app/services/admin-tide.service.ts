import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { Tide, TideInstance } from './tide.service';

@Injectable({ providedIn: 'root' })
export class AdminTideService {
    private http = inject(HttpClient);

    // Admin: list all tide configs
    getTides(): Observable<{ success: boolean; tides: Tide[] }> {
        return this.http.get<{ success: boolean; tides: Tide[] }>('/api/admin/tides');
    }

    // Admin: create or update a tide config (id=null for new)
    saveTide(tide: Partial<Tide>): Observable<{ success: boolean; tide_id?: string; error?: string }> {
        return this.http.post<any>('/api/admin/tide', tide);
    }

    // Admin: delete a tide config
    deleteTide(id: string): Observable<{ success: boolean; error?: string }> {
        return this.http.delete<any>('/api/admin/tide', { body: { id } });
    }

    // Admin: list all running instances across all users
    getInstances(): Observable<{ success: boolean; instances: TideInstance[] }> {
        return this.http.get<{ success: boolean; instances: TideInstance[] }>('/api/admin/instances');
    }

    // Admin: force-destroy any instance
    deleteInstance(id: string): Observable<{ success: boolean; error?: string }> {
        return this.http.delete<any>('/api/admin/instance', { body: { id } });
    }

    pauseInstance(id: string): Observable<{ success: boolean; error?: string }> {
        return this.http.post<any>(`/api/admin/instance/${id}/pause`, {});
    }

    unpauseInstance(id: string): Observable<{ success: boolean; error?: string }> {
        return this.http.post<any>(`/api/admin/instance/${id}/unpause`, {});
    }

    // Admin: Docker networks list
    getNetworks(): Observable<{ success: boolean; networks: string[] }> {
        return this.http.get<any>('/api/admin/networks');
    }

    // Admin: list agents (for tide agent-limit picker)
    getAgents(): Observable<{ success: boolean; agents: { id: string; display_name: string }[] }> {
        return this.http.get<any>('/api/admin/agents');
    }

    // Admin: upload tide image, returns served URL
    uploadTideImage(file: File): Observable<{ success: boolean; url: string; error?: string }> {
        const form = new FormData();
        form.append('file', file);
        return this.http.post<any>('/api/admin/tide/image', form);
    }
}
