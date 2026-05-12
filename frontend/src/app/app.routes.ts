import { Routes } from '@angular/router';
import { adminGuard } from './guards/admin.guard';
import { authGuard } from './guards/auth.guard';
import { AppLayout } from './layout/component/app.layout';
import { Dashboard } from './pages/dashboard/dashboard';
import { Notfound } from './pages/notfound/notfound';

export const appRoutes: Routes = [
    {
        path: '',
        component: AppLayout,
        canActivate: [authGuard],
        children: [
            { path: '', component: Dashboard },

            // User-facing pages
            {
                path: 'tides',
                loadComponent: () => import('./pages/tides/tides').then(m => m.Tides)
            },
            {
                path: 'profile',
                loadComponent: () => import('./pages/profile/profile').then(m => m.ProfileComponent)
            },

            // Admin pages
            {
                path: 'admin/tides',
                loadComponent: () => import('./pages/admin/tides/admin-tides').then(m => m.AdminTides),
                canActivate: [adminGuard]
            },
            {
                path: 'admin/instances',
                loadComponent: () => import('./pages/admin/instances/admin-instances').then(m => m.AdminInstances),
                canActivate: [adminGuard]
            },
            {
                path: 'admin/agents',
                loadComponent: () => import('./pages/admin/agents/admin-agents').then(m => m.AdminAgents),
                canActivate: [adminGuard]
            },
            {
                path: 'admin/registry',
                loadComponent: () => import('./pages/admin/registry/admin-registry').then(m => m.AdminRegistry),
                canActivate: [adminGuard]
            },
            {
                path: 'admin/logs',
                loadComponent: () => import('./pages/admin/logs/admin-logs').then(m => m.AdminLogs),
                canActivate: [adminGuard]
            },
            {
                path: 'admin/system',
                loadComponent: () => import('./pages/admin/system/admin-system').then(m => m.AdminSystem),
                canActivate: [adminGuard]
            },
            {
                path: 'admin/users',
                loadComponent: () => import('./pages/admin/users/users').then(m => m.UsersComponent),
                canActivate: [adminGuard]
            },
            {
                path: 'admin/groups',
                loadComponent: () => import('./pages/admin/groups/groups').then(m => m.GroupsComponent),
                canActivate: [adminGuard]
            },
            {
                path: 'admin/auth-providers',
                loadComponent: () => import('./pages/admin/auth-providers/auth-providers').then(m => m.AuthProvidersComponent),
                canActivate: [adminGuard]
            },
            {
                path: 'admin/storage',
                loadComponent: () => import('./pages/admin/storage/admin-storage').then(m => m.AdminStorage),
                canActivate: [adminGuard]
            },
        ]
    },
    { path: 'notfound', component: Notfound },
    {
        path: 'session/:instanceId',
        loadComponent: () => import('./pages/session/session').then(m => m.SessionPage)
    },
    { path: 'auth', loadChildren: () => import('./pages/auth/auth.routes') },
    { path: '**', redirectTo: '/notfound' }
];
