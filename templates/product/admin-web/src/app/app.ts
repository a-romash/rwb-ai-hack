import {ChangeDetectionStrategy, Component, computed, inject} from '@angular/core';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatToolbarModule} from '@angular/material/toolbar';
import {RouterOutlet} from '@angular/router';
import {MODEL} from './generated/model';
import {AppMenu} from './screens/menu';
import {LiveEvents} from './screens/events';
import {Session} from './screens/session';

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatToolbarModule, MatSidenavModule, RouterOutlet, AppMenu],
  template: `
    <mat-toolbar>
      <span>{{ title }}</span>
      <span class="spacer"></span>
      @if (live.notifications().length; as count) {
        <span class="badge" data-testid="app.notifications-count" role="status" [title]="latest()">{{ count }}</span>
      }
      @if (session.role(); as role) {
        <span class="role" data-testid="app.role">{{ roles[role] ?? role }}</span>
      }
    </mat-toolbar>
    <mat-sidenav-container class="shell">
      <mat-sidenav mode="side" opened>
        <app-menu />
      </mat-sidenav>
      <mat-sidenav-content>
        <router-outlet />
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: `
    :host { display: flex; flex-direction: column; min-height: 100vh; }
    .shell { flex: 1; }
    .spacer { flex: 1; }
    .badge { min-width: 24px; padding: 2px 8px; border-radius: 999px; background: #b3261e; color: #fff; font-size: 0.8125rem; text-align: center; }
    .role { font-size: 0.875rem; opacity: 0.8; }
    mat-sidenav { width: 220px; }
  `,
})
export class App {
  readonly session = inject(Session);
  readonly live = inject(LiveEvents);
  readonly latest = computed(() => this.live.notifications().map((item) => item.text).join('\n'));
  readonly title = MODEL.title || 'Admin';
  readonly roles = MODEL.roles;

  constructor() {
    document.documentElement.lang = MODEL.lang;
  }
}
