import {registerLocaleData} from '@angular/common';
import localeRu from '@angular/common/locales/ru';
import {LOCALE_ID} from '@angular/core';
import {provideHttpClient} from '@angular/common/http';
import {bootstrapApplication} from '@angular/platform-browser';
import {provideRouter} from '@angular/router';
import {provideTaiga} from '@taiga-ui/core';
import {TUI_LANGUAGE, TUI_RUSSIAN_LANGUAGE} from '@taiga-ui/i18n';
import {of} from 'rxjs';
import {App} from './app/app';
import {routes} from './app/routes';

registerLocaleData(localeRu);
bootstrapApplication(App, {
  providers: [
    provideHttpClient(), provideRouter(routes), ...provideTaiga(),
    {provide: LOCALE_ID, useValue: 'ru'},
    {provide: TUI_LANGUAGE, useValue: of(TUI_RUSSIAN_LANGUAGE)},
  ],
}).catch(console.error);
