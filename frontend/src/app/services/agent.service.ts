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

export interface AgentInstanceStat {
    instance_id: string;
    container_name: string;
    status: string;
    cpu_percent: number;
    mem_usage_bytes: number;
    mem_limit_bytes: number;
    net_rx_bytes: number;
    net_tx_bytes: number;
    pids: number;
    tide_name?: string;
    username?: string;
}

export interface AgentStatsResponse {
    success: boolean;
    error?: string;
    agent_name?: string;
    total_cores?: number;
    total_memory?: number;
    instances: AgentInstanceStat[];
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

    getAgentStats(agentId: string): Observable<AgentStatsResponse> {
        return this.http.get<AgentStatsResponse>(`/api/admin/agent/${agentId}/stats`);
    }
}
