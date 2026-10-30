import {registerLocaleData} from '@angular/common';
import {provideHttpClient, withFetch} from '@angular/common/http';
import localeRu from '@angular/common/locales/ru';
import {ApplicationConfig, LOCALE_ID, provideBrowserGlobalErrorListeners, provideZoneChangeDetection, signal} from '@angular/core';
import {provideRouter, withComponentInputBinding, withInMemoryScrolling} from '@angular/router';
import {provideTaiga} from '@taiga-ui/core';
import {TUI_LANGUAGE, TUI_RUSSIAN_LANGUAGE} from '@taiga-ui/i18n';
import {routes} from './app.routes';

registerLocaleData(localeRu);

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({eventCoalescing: true}),
    provideHttpClient(withFetch()),
    provideRouter(routes, withComponentInputBinding(), withInMemoryScrolling({scrollPositionRestoration: 'top'})),
    provideTaiga(),
    {provide: LOCALE_ID, useValue: 'ru'},
    // В Taiga UI 5 язык — Signal, а не Observable
    {provide: TUI_LANGUAGE, useValue: signal(TUI_RUSSIAN_LANGUAGE)},
  ],
};
