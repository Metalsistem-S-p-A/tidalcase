import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/** @deprecated Use permissionGuard instead */
export const certManagerGuard: CanActivateFn = (_route, _state) => {
    const authService = inject(AuthService);
    const router = inject(Router);

    if (authService.hasPermission('certificates', 'write')) {
        return true;
    }

    router.navigate(['/auth/access']);
    return false;
};
