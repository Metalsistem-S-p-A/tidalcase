import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { switchMap } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = (_route, state) => {
    const authService = inject(AuthService);
    const router = inject(Router);

    if (authService.isAuthenticated()) {
        return true;
    }

    return authService.tryMe().pipe(
        switchMap(ok => {
            if (ok) return [true] as const;
            return authService.tryRefresh();
        }),
        switchMap(ok => {
            if (ok) return [true] as const;
            router.navigate(['/auth/login'], { queryParams: { returnUrl: state.url } });
            return [false] as const;
        })
    );
};
