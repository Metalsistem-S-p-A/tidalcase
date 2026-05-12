import { Component, effect, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { AuthService } from './app/services/auth.service';
import { LanguageService } from './app/services/language.service';

@Component({
    selector: 'app-root',
    standalone: true,
    imports: [RouterModule],
    templateUrl: './app.component.html'
})
export class AppComponent {
    private auth = inject(AuthService);
    private languageService = inject(LanguageService);

    constructor() {
        effect(() => {
            const lang = this.auth.currentUser()?.settings?.['preferred_language'];
            if (!lang || lang === 'system') return;
            if (lang !== this.languageService.selectedLang()) {
                this.languageService.applyLanguage(lang);
            }
        });
    }
}
