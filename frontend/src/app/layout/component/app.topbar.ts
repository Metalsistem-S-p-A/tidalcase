import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { StyleClassModule } from 'primeng/styleclass';
import { AuthService } from '../../services/auth.service';
import { LayoutService } from '../service/layout.service';
import { AppConfigurator } from './app.configurator';
import { AppLanguageSelector } from './app.languageselector';

@Component({
    selector: 'app-topbar',
    standalone: true,
    imports: [RouterModule, CommonModule, StyleClassModule, AppConfigurator, AppLanguageSelector, TranslateModule, FormsModule],
    templateUrl: './app.topbar.html'
})
export class AppTopbar {
    public layoutService = inject(LayoutService);
    private authService = inject(AuthService);
    private router = inject(Router);

    get isAuthenticated(): boolean {
        return this.authService.isAuthenticated();
    }

    toggleDarkMode() {
        this.layoutService.layoutConfig.update((state) => ({ ...state, theme: state.theme }));
    }

    goToProfile() {
        this.router.navigate(['/profile']);
    }

    goToJobs() {
        this.router.navigate(['/jobs']);
    }

    logout() {
        this.authService.logout();
    }
}