import {ChangeDetectionStrategy, Component, computed, inject, signal} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatToolbarModule} from '@angular/material/toolbar';
import {RouterLink, RouterLinkActive, RouterOutlet} from '@angular/router';
import {MODEL} from './generated/model';
import {LiveEvents} from './screens/events';
import {Session} from './screens/session';

/** Mobile shell: top bar, the screen, and the role's menu as a bottom tab bar. */
@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatToolbarModule, MatButtonModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <mat-toolbar>
      <span class="title">{{ title }}</span>
      <span class="spacer"></span>
      @if (live.notifications().length; as count) {
        <span class="badge" data-testid="app.notifications-count" role="status" [title]="latest()">{{ count }}</span>
      }
      @if (!online()) {
        <span class="offline" role="status">Нет сети</span>
      }
      @if (canNotify()) {
        <button mat-button type="button" data-testid="app.notifications" (click)="askNotifications()">
          Уведомления
        </button>
      }
    </mat-toolbar>
    <main>
      <router-outlet />
    </main>
    @if (tabs().length) {
      <nav class="tabs" aria-label="Меню">
        @for (tab of tabs(); track tab.path) {
          <a [routerLink]="['/' + tab.path]" routerLinkActive="active">{{ tab.title }}</a>
        }
        <a routerLink="/" (click)="session.use('')">Роль</a>
      </nav>
    }
  `,
  styles: `
    :host { display: flex; flex-direction: column; min-height: 100dvh; }
    mat-toolbar { position: sticky; top: 0; z-index: 2; padding-top: env(safe-area-inset-top); }
    .title { overflow: hidden; text-overflow: ellipsis; }
    .spacer { flex: 1; }
    .badge { min-width: 24px; padding: 2px 8px; border-radius: 999px; background: #b3261e; color: #fff; font-size: 0.8125rem; text-align: center; }
    .offline { font-size: 0.8125rem; padding: 2px 8px; border-radius: 999px; background: #fdecea; color: #8c1d18; }
    main { flex: 1; padding-bottom: 72px; }
    .tabs {
      position: fixed; inset: auto 0 0 0; display: flex; justify-content: space-around;
      padding: 8px 8px calc(8px + env(safe-area-inset-bottom));
      background: var(--mat-sys-surface-container, #f4f6f8);
      border-top: 1px solid var(--mat-sys-outline-variant, #e0e0e0);
    }
    .tabs a { flex: 1; text-align: center; padding: 10px 4px; border-radius: 12px; color: inherit; text-decoration: none; font-size: 0.875rem; }
    .tabs a.active { background: var(--mat-sys-secondary-container, #e8eaf6); font-weight: 600; }
  `,
  host: {'(window:online)': 'online.set(true)', '(window:offline)': 'online.set(false)'},
})
export class App {
  readonly session = inject(Session);
  readonly live = inject(LiveEvents);
  readonly latest = computed(() => this.live.notifications().map((item) => item.text).join('\n'));
  readonly title = MODEL.title || 'Mobile';
  readonly online = signal(navigator.onLine);
  readonly permission = signal(typeof Notification === 'undefined' ? 'denied' : Notification.permission);
  readonly canNotify = computed(() => MODEL.device.includes('local_notification') && this.permission() === 'default');
  readonly tabs = computed(() =>
    (MODEL.menus[this.session.role() ?? ''] ?? [])
      .filter((path) => MODEL.screens[path])
      .map((path) => ({path, title: MODEL.screens[path].title})),
  );

  constructor() {
    document.documentElement.lang = MODEL.lang;
  }

  async askNotifications(): Promise<void> {
    this.permission.set(await Notification.requestPermission());
  }
}
