import {ApplicationConfig, isDevMode, provideBrowserGlobalErrorListeners, provideZoneChangeDetection} from '@angular/core';
import {provideAnimationsAsync} from '@angular/platform-browser/animations/async';
import {provideRouter} from '@angular/router';
import {provideServiceWorker} from '@angular/service-worker';
import {environment} from '../environments/environment';
import {API_BASE_URL} from './api/sse';
import {routes} from './routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({eventCoalescing: true}),
    provideRouter(routes),
    provideAnimationsAsync(),
    {provide: API_BASE_URL, useValue: environment.apiBaseUrl},
    // Offline shell and cached reads: the PWA keeps working in a dead zone (ui.json state `offline`).
    provideServiceWorker('ngsw-worker.js', {enabled: !isDevMode(), registrationStrategy: 'registerWhenStable:30000'}),
  ],
};
