import { CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { RouterModule } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { MenuItem } from 'primeng/api';
import { AuthService } from '../../services/auth.service';
import { AppMenuitem } from './app.menuitem';

@Component({
    selector: 'app-menu',
    standalone: true,
    imports: [CommonModule, AppMenuitem, RouterModule, TranslateModule],
    templateUrl: './app.menu.html'
})
export class AppMenu implements OnInit {
    model: MenuItem[] = [];
    private authService = inject(AuthService);
    private translate = inject(TranslateService);

    ngOnInit() {
        this.loadMenu();
        this.translate.onLangChange.subscribe(() => this.loadMenu());
    }

    loadMenu() {
        const isAdmin = this.authService.isAdmin();
        const menuItems: MenuItem[] = [];

        // Main section — always visible
        menuItems.push({
            label: this.translate.instant('menu.main'),
            items: [
                { label: this.translate.instant('dashboard.title'), icon: 'pi pi-fw pi-home', routerLink: ['/'] },
                { label: this.translate.instant('menu.tides'), icon: 'pi pi-fw pi-desktop', routerLink: ['/tides'] },
            ]
        });

        // Admin section
        if (isAdmin) {
            menuItems.push({
                label: this.translate.instant('menu.administration'),
                items: [
                    { label: this.translate.instant('menu.adminTides'), icon: 'pi pi-fw pi-server', routerLink: ['/admin/tides'] },
                    { label: this.translate.instant('menu.adminInstances'), icon: 'pi pi-fw pi-list', routerLink: ['/admin/instances'] },
                    { label: this.translate.instant('menu.adminAgents'), icon: 'pi pi-fw pi-share-alt', routerLink: ['/admin/agents'] },
                    { label: this.translate.instant('menu.adminRegistry'), icon: 'pi pi-fw pi-box', routerLink: ['/admin/registry'] },
                    { label: this.translate.instant('menu.users'), icon: 'pi pi-fw pi-users', routerLink: ['/admin/users'] },
                    { label: this.translate.instant('menu.groups'), icon: 'pi pi-fw pi-sitemap', routerLink: ['/admin/groups'] },
                    { label: this.translate.instant('menu.authProviders'), icon: 'pi pi-fw pi-lock', routerLink: ['/admin/auth-providers'] },
                    { label: this.translate.instant('menu.adminStorage'), icon: 'pi pi-fw pi-database', routerLink: ['/admin/storage'] },
                    { label: this.translate.instant('menu.adminLogs'), icon: 'pi pi-fw pi-file-edit', routerLink: ['/admin/logs'] },
                    { label: this.translate.instant('menu.adminSystem'), icon: 'pi pi-fw pi-info-circle', routerLink: ['/admin/system'] },
                ]
            });
        }

        this.model = menuItems;
    }
}
