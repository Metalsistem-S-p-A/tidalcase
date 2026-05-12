import { CommonModule } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { SelectButtonModule } from 'primeng/selectbutton';
import { LanguageService } from '../../services/language.service';

@Component({
    selector: 'app-language-selector',
    standalone: true,
    imports: [CommonModule, FormsModule, SelectButtonModule, TranslateModule],
    templateUrl: './app.languageselector.html',
    host: {
        class: 'hidden absolute top-13 right-0 w-72 p-4 bg-surface-0 dark:bg-surface-900 border border-surface rounded-border origin-top shadow-[0px_3px_5px_rgba(0,0,0,0.02),0px_0px_2px_rgba(0,0,0,0.05),0px_1px_4px_rgba(0,0,0,0.08)]'
    }
})
export class AppLanguageSelector {
    private languageService = inject(LanguageService);

    languages = [
        { label: 'System', value: 'system' },
        { label: 'English', value: 'en' },
        { label: 'Italiano', value: 'it' }
    ];

    selectedLanguage = computed(() => this.languageService.selectedLang());

    changeLanguage(lang: string) {
        this.languageService.changeLanguage(lang);
    }
}