import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
    const authService = inject(AuthService);
    const router = inject(Router);

    return next(req).pipe(
        catchError((error) => {
            // Handle 401 Unauthorized errors
            if (error.status === 401) {
                // JWT token is invalid, expired, or missing
                // Clear session and redirect to login
                authService.logout();

                // Don't redirect if already on login page
                if (!router.url.includes('/auth/login')) {
                    router.navigate(['/auth/login'], {
                        queryParams: { expired: 'true' }
                    });
                }
            }

            return throwError(() => error);
        })
    );
};
