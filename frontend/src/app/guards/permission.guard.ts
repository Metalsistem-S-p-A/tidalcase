import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const permissionGuard: CanActivateFn = (route: ActivatedRouteSnapshot, _state) => {
    const authService = inject(AuthService);
    const router = inject(Router);
    const resource = route.data['resource'] as string;
    const level = (route.data['level'] as 'read' | 'write') || 'read';

    if (!authService.isAuthenticated()) {
        router.navigate(['/auth/login']);
        return false;
    }
    if (authService.hasPermission(resource, level)) return true;
    router.navigate(['/']);
    return false;
};
