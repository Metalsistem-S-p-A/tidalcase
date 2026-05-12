import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { Agent } from './agent.service';

export interface Tide {
    id: string;
    display_name: string;
    description?: string;
    image_path?: string;
    tide_type: 'container' | 'vnc' | 'rdp' | 'ssh';
    container_docker_image?: string;
    container_docker_registry?: string;
    container_cores?: number;
    container_memory?: string;
    container_swap?: string;
    container_persistent_profile_path?: string;
    container_network?: string;
    server_ip?: string;
    server_port?: number;
    restricted_groups?: string;
    session_time_limit?: number;
    session_idle_time_limit?: number;
    agent_selection_mode?: 'auto' | 'fixed' | 'restricted';
    agents?: { id: string; display_name: string }[];
    vnc_user?: string;
    upload_path?: string;
    download_path?: string;
    open_mode?: 'user' | 'current' | 'tab' | 'window';
    connection_settings?: Record<string, any>;
    requires_credentials?: boolean;
}

export interface TideInstance {
    id: string;
    created_at: string;
    updated_at: string;
    ip?: string;
    tide: Partial<Tide>;
    agent: Partial<Agent>;
    user: { id: string; username: string };
    screenshotUrl?: string;
    vnc_url?: string;
    guac_token?: string;
}

export interface RequestInstancePayload {
    tide_id: string;
    resolution?: string;
    language: string;
    credentials?: { username?: string; password?: string; domain?: string };
}

export interface SessionFile {
    name: string;
    size: number;
    modified: number;
}

@Injectable({ providedIn: 'root' })
export class TideService {
    private http = inject(HttpClient);

    // User-facing: list available tides
    getTides(): Observable<{ success: boolean; tides: Tide[] }> {
        return this.http.get<{ success: boolean; tides: Tide[] }>('/api/tides');
    }
    

    // User-facing: list own running instances
    getMyInstances(): Observable<{ success: boolean; instances: TideInstance[] }> {
        return this.http.get<{ success: boolean; instances: TideInstance[] }>('/api/instances');
    }

    // User-facing: request a new instance
    requestInstance(payload: RequestInstancePayload): Observable<{ success: boolean; instance_id?: string; error?: string; pulling?: boolean; open_mode?: string; agent_id?: string; image?: string }> {
        return this.http.post<any>('/api/instance/request', payload);
    }

    getPullStatus(agentId: string, image: string): Observable<{ success: boolean; status: string; percent: number; layers_done?: number; layers_total?: number; error?: string }> {
        return this.http.get<any>('/api/pull-status', { params: { agent_id: agentId, image } });
    }
    
    checkInstance(instanceId: string): Observable<{exists: boolean}> {
        return this.http.get<any>(`/api/tide/${instanceId}/exists`);
    }

    // User-facing: get instance info (used by tide session page)
    getInstanceInfo(instanceId: string): Observable<any> {
        return this.http.get<any>(`/api/tide/${instanceId}/info`);
    }

    // User-facing: destroy own instance
    destroyInstance(instanceId: string): Observable<{ success: boolean }> {
        return this.http.get<{ success: boolean }>(`/api/instance/${instanceId}/destroy`);
    }

    getTideInfo(instanceId: string): Observable<{ success: boolean; guacamole: boolean; guac_token: string; vnc_url: string }> {
        return this.http.get<any>(`/api/tide/${instanceId}/info`);
    }

    listDownloads(instanceId: string): Observable<{ success: boolean; files: SessionFile[] }> {
        return this.http.get<any>(`/api/instance/${instanceId}/files/downloads`);
    }

    downloadFile(instanceId: string, filename: string): Observable<Blob> {
        return this.http.get(`/api/instance/${instanceId}/files/downloads/${encodeURIComponent(filename)}`, {
            responseType: 'blob',
        });
    }

    uploadFile(instanceId: string, files: FileList): Observable<{ success: boolean; name?: string; error?: string }> {
        const form = new FormData();
        for (const file of files) {
            form.append('file[]', file);
        }
        return this.http.post<any>(`/api/instance/${instanceId}/files/uploads`, form);
    }
}
