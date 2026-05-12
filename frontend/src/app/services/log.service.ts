import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface LogEntry {
    id: number;
    created_at: string;
    level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
    message: string;
}

export interface LogsResponse {
    success: boolean;
    logs: LogEntry[];
    pagination: {
        page: number;
        per_page: number;
        total: number;
        pages: number;
    };
}

@Injectable({ providedIn: 'root' })
export class LogService {
    private http = inject(HttpClient);

    getLogs(page = 1, perPage = 50, level?: string): Observable<LogsResponse> {
        let params: any = { page, per_page: perPage };
        if (level) params['type'] = level;
        return this.http.get<LogsResponse>('/api/admin/logs', { params });
    }
}
