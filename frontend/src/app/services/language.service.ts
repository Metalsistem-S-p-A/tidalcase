import { Injectable, inject, signal } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { PrimeNG } from 'primeng/config';
import { AuthService } from './auth.service';

@Injectable({
    providedIn: 'root'
})
export class LanguageService {
    private translate = inject(TranslateService);
    private primeNG = inject(PrimeNG);
    private authService = inject(AuthService);

    readonly currentLang = signal<string>('en');
    readonly selectedLang = signal<string>('system');

    constructor() {
        this.translate.addLangs(['en', 'it']);
        const stored = this.authService.currentUser()?.settings?.['preferred_language'] ?? 'system';
        const resolved = this.resolve(stored);
        this.translate.use(resolved).subscribe(() => this.setPrimeNGTranslations());
        this.currentLang.set(resolved);
        this.selectedLang.set(stored);
    }

    applyLanguage(lang: string): void {
        const resolved = this.resolve(lang);
        this.translate.use(resolved).subscribe(() => this.setPrimeNGTranslations());
        this.currentLang.set(resolved);
        this.selectedLang.set(lang);
    }

    changeLanguage(lang: string): void {
        this.applyLanguage(lang);
        this.authService.updateLanguage(lang).subscribe();
    }

    getCurrentLang(): string {
        return this.translate.getCurrentLang();
    }

    private resolve(lang: string): string {
        if (lang === 'system') {
            const browserLang = this.translate.getBrowserLang();
            return browserLang?.match(/en|it/) ? browserLang : 'en';
        }
        return ['en', 'it'].includes(lang) ? lang : 'en';
    }

    private setPrimeNGTranslations(): void {
        this.translate.get('primeng').subscribe((translations: unknown) => {
            this.primeNG.setTranslation(translations as Record<string, unknown>);
        });
    }
}
