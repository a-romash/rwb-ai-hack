import {ChangeDetectionStrategy, Component} from '@angular/core';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatToolbarModule} from '@angular/material/toolbar';
import {RouterOutlet} from '@angular/router';
import {AppMenuPlaceholder} from './menu-placeholder';

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatToolbarModule, MatSidenavModule, RouterOutlet, AppMenuPlaceholder],
  template: `
    <mat-toolbar>
      <span>Admin</span>
    </mat-toolbar>
    <mat-sidenav-container class="shell">
      <mat-sidenav mode="side" opened>
        <app-menu-placeholder />
      </mat-sidenav>
      <mat-sidenav-content>
        <router-outlet />
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: `
    :host { display: flex; flex-direction: column; min-height: 100vh; }
    .shell { flex: 1; }
    mat-sidenav { width: 220px; }
  `,
})
export class App {}
