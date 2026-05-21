import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
    const authService = inject(AuthService);
    const router = inject(Router);

    return next(req).pipe(
        catchError((error) => {
            if (error.status === 401 && !req.url.includes('/api/auth/')) {
                return authService.tryRefresh().pipe(
                    switchMap((refreshed) => {
                        if (refreshed) {
                            return next(req);
                        }
                        authService.logout();
                        if (!router.url.includes('/auth/login')) {
                            router.navigate(['/auth/login'], { queryParams: { expired: 'true' } });
                        }
                        return throwError(() => error);
                    }),
                    catchError(() => {
                        authService.logout();
                        if (!router.url.includes('/auth/login')) {
                            router.navigate(['/auth/login'], { queryParams: { expired: 'true' } });
                        }
                        return throwError(() => error);
                    })
                );
            }

            return throwError(() => error);
        })
    );
};
