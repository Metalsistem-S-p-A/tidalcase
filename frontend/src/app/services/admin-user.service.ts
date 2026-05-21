import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface TidalcaseUser {
    id: string;
    username: string;
    usertype: 'Internal' | 'External';
    protected: boolean;
    created_at?: string;
    groups: { id: string; display_name: string }[];
    auto_start_tide_id?: string | null;
    preferred_language: string;
}

@Injectable({
    providedIn: 'root'
})
export class AdminUserService {
    private readonly http = inject(HttpClient);
    private readonly LIST_URL = '/api/admin/users';
    private readonly ITEM_URL = '/api/admin/user';

    getUsers(): Observable<{ data: TidalcaseUser[]; totalRecords: number }> {
        return this.http.get<{ data: TidalcaseUser[]; totalRecords: number }>(this.LIST_URL);
    }

    createUser(payload: { username: string; password: string; usertype: string; groups: string[]; auto_start_tide_id?: string | null, preferred_language: string}): Observable<{ success: boolean }> {
        return this.http.post<{ success: boolean }>(this.ITEM_URL, { id: null, ...payload });
    }

    updateUser(id: string, payload: { username: string; groups: string[]; auto_start_tide_id?: string | null, preferred_language: string }): Observable<{ success: boolean }> {
        return this.http.post<{ success: boolean }>(this.ITEM_URL, { id, ...payload });
    }

    deleteUser(id: string): Observable<{ success: boolean }> {
        return this.http.delete<{ success: boolean }>(this.ITEM_URL, { body: { id } });
    }
}
