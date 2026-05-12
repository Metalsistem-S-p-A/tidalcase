import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface SystemInfo {
    success: boolean;
    system: {
        hostname: string;
        os: string;
    };
    version: {
        tidalcase: string;
        python: string;
        docker: string;
        nginx: string;
    };
}

@Injectable({ providedIn: 'root' })
export class SystemService {
    private http = inject(HttpClient);

    getSystemInfo(): Observable<SystemInfo> {
        return this.http.get<SystemInfo>('/api/admin/system_info');
    }
}
