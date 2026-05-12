import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { ApplicationConfig } from '@angular/core';
import { provideRouter, withEnabledBlockingInitialNavigation, withInMemoryScrolling } from '@angular/router';
import { provideMissingTranslationHandler, provideTranslateService } from "@ngx-translate/core";
import { provideTranslateHttpLoader } from "@ngx-translate/http-loader";
import Aura from '@primeuix/themes/aura';
import { ConfirmationService, MessageService } from 'primeng/api';
import { providePrimeNG } from 'primeng/config';
import { appRoutes } from './app/app.routes';
import { authInterceptor } from './app/interceptors/auth.interceptor';
import { errorInterceptor } from './app/interceptors/error.interceptor';

import { registerLocaleData } from '@angular/common';
import localeEn from '@angular/common/locales/en';
import localeIt from '@angular/common/locales/it';
import { MissingTranslationExceptionHandler } from './app/handlers/missingtranslationexception.handler';

// Register locales
registerLocaleData(localeIt);
registerLocaleData(localeEn);

export const appConfig: ApplicationConfig = {
    providers: [
        provideRouter(appRoutes, withInMemoryScrolling({ anchorScrolling: 'enabled', scrollPositionRestoration: 'enabled' }), withEnabledBlockingInitialNavigation()),
        provideHttpClient(withFetch(), withInterceptors([authInterceptor, errorInterceptor])),
        providePrimeNG({
            theme: {
                preset: Aura,
                options: { darkModeSelector: '.app-dark' }
            },
            ripple: true,
            zIndex: {
                modal: 1100,
                overlay: 1000,
                menu: 1000,
                tooltip: 1100
            }
        }),
        provideTranslateService({
            loader: provideTranslateHttpLoader({
                prefix: './i18n/',
                suffix: '.json'
            }),
            missingTranslationHandler:
                provideMissingTranslationHandler(MissingTranslationExceptionHandler),
            fallbackLang: 'en',
            lang: (() => {
                try {
                    const saved = localStorage.getItem('language');
                    if (saved) return (JSON.parse(saved).language ?? 'en');
                } catch {}
                return 'en';
            })()
        }),
        MessageService,
        ConfirmationService
    ]
};
