import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatToolbarModule} from '@angular/material/toolbar';
import {RouterOutlet} from '@angular/router';
import {MODEL} from './generated/model';
import {AppMenu} from './screens/menu';
import {Session} from './screens/session';

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatToolbarModule, MatSidenavModule, RouterOutlet, AppMenu],
  template: `
    <mat-toolbar>
      <span>{{ title }}</span>
      <span class="spacer"></span>
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
    .role { font-size: 0.875rem; opacity: 0.8; }
    mat-sidenav { width: 220px; }
  `,
})
export class App {
  readonly session = inject(Session);
  readonly title = MODEL.title || 'Admin';
  readonly roles = MODEL.roles;

  constructor() {
    document.documentElement.lang = MODEL.lang;
  }
}
