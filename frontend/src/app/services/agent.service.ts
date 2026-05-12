import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface Agent {
    id?: string;
    display_name: string;
    docker_host: string;
    total_cores?: number;
    total_memory?: number;
    enabled: boolean;
    healthy?: boolean;
    last_healthcheck_at?: string;
    created_at?: string;
    prune_mode?: 'off' | 'normal' | 'aggressive';
    api_url?: string;
    api_token?: string;
}

@Injectable({ providedIn: 'root' })
export class AgentService {
    private http = inject(HttpClient);

    getAgents(): Observable<{ success: boolean; agents: Agent[]; join_token: string }> {
        return this.http.get<any>('/api/admin/agents');
    }

    saveAgent(agent: Partial<Agent>): Observable<{ success: boolean; error?: string }> {
        return this.http.post<any>('/api/admin/agent', agent);
    }

    deleteAgent(id: string): Observable<{ success: boolean; error?: string }> {
        return this.http.delete<any>('/api/admin/agent', { body: { id } });
    }

    testAgent(agent: Partial<Agent>): Observable<{ success: boolean; message?: string; error?: string }> {
        return this.http.post<any>('/api/admin/agent/test', agent);
    }

    healthcheck(agentId: string): Observable<{ success: boolean; error?: string }> {
        return this.http.post<any>(`/api/admin/agent/${agentId}/healthcheck`, {});
    }

    prune(agentId: string): Observable<{ success: boolean; error?: string }> {
        return this.http.post<any>(`/api/admin/agent/${agentId}/prune`, {});
    }
}
