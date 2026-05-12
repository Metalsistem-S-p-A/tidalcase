import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface GroupPermissions {
    admin_panel: boolean;
    view_instances: boolean;
    edit_instances: boolean;
    view_users: boolean;
    edit_users: boolean;
    view_tides: boolean;
    edit_tides: boolean;
    view_registry: boolean;
    edit_registry: boolean;
    view_groups: boolean;
    edit_groups: boolean;
}

export interface GroupSettings {
    max_sessions_per_user: number;
    allow_audio: boolean | null;
    allow_downloads: boolean | null;
    allow_uploads: boolean | null;
    auto_start_tide_id?: string | null;
}

export interface Group {
    id: string;
    display_name: string;
    protected: boolean;
    priority: number;
    settings: GroupSettings;
    permissions: GroupPermissions;
}

export interface GroupPayload {
    id: string | null;
    display_name: string;
    priority: number;
    settings: GroupSettings;
    perm_admin_panel: boolean;
    perm_view_instances: boolean;
    perm_edit_instances: boolean;
    perm_view_users: boolean;
    perm_edit_users: boolean;
    perm_view_tides: boolean;
    perm_edit_tides: boolean;
    perm_view_registry: boolean;
    perm_edit_registry: boolean;
    perm_view_groups: boolean;
    perm_edit_groups: boolean;
}

@Injectable({
    providedIn: 'root'
})
export class GroupService {
    private readonly http = inject(HttpClient);
    private readonly LIST_URL = '/api/admin/groups';
    private readonly ITEM_URL = '/api/admin/group';

    getGroups(): Observable<{ data: Group[]; totalRecords: number }> {
        return this.http.get<{ data: Group[]; totalRecords: number }>(this.LIST_URL);
    }

    saveGroup(payload: GroupPayload): Observable<{ success: boolean }> {
        return this.http.post<{ success: boolean }>(this.ITEM_URL, payload);
    }

    deleteGroup(id: string): Observable<{ success: boolean }> {
        return this.http.delete<{ success: boolean }>(this.ITEM_URL, { body: { id } });
    }
}
