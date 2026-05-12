import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({
    providedIn: 'root'
})
export class UserService {
    private apiUrl = "/api";
    private http = inject(HttpClient);

    changePassword(currentPassword: string, newPassword: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/users/change-password`, {
            currentPassword,
            newPassword
        });
    }

    forgotPassword(username: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/auth/forgot-password`, {
            username
        });
    }

    resetPassword(token: string, newPassword: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/auth/reset-password/${token}`, {
            newPassword
        });
    }

    getCurrentUser(): Observable<any> {
        return this.http.get(`${this.apiUrl}/users/me`);
    }

    updateEmail(email: string): Observable<any> {
        return this.http.put(`${this.apiUrl}/users/email`, {
            email
        });
    }

    updateAutostartTide(tide_id: string): Observable<any> {
        return this.http.put(`${this.apiUrl}/users/autostart-tide`, {
            tide_id
        });
    }

    // MFA methods
    setupMFA(): Observable<any> {
        return this.http.post(`${this.apiUrl}/users/mfa/setup`, {});
    }

    verifyAndEnableMFA(token: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/users/mfa/verify`, {
            token
        });
    }

    disableMFA(password: string, token: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/users/mfa/disable`, {
            password,
            token
        });
    }

    updateMfaTrustDuration(duration: number): Observable<any> {
        return this.http.put(`${this.apiUrl}/users/mfa/trust-duration`, {
            mfaTrustDuration: duration
        });
    }

    getTrustedDevices(): Observable<any> {
        return this.http.get(`${this.apiUrl}/users/mfa/trusted-devices`);
    }

    revokeTrustedDevice(deviceId: string): Observable<any> {
        return this.http.delete(`${this.apiUrl}/users/mfa/trusted-devices/${deviceId}`);
    }

    revokeAllTrustedDevices(): Observable<any> {
        return this.http.delete(`${this.apiUrl}/users/mfa/trusted-devices`);
    }

    // Notification methods
    updateNotificationEvents(events: string[]): Observable<any> {
        return this.http.put(`${this.apiUrl}/users/notification-events`, {
            notificationEvents: events
        });
    }
}
