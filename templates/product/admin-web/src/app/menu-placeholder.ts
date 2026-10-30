import {ChangeDetectionStrategy, Component} from '@angular/core';
import {MatListModule} from '@angular/material/list';
import {RouterLink} from '@angular/router';

@Component({
  selector: 'app-menu-placeholder',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatListModule, RouterLink],
  template: `
    <nav aria-label="Main">
      <mat-nav-list>
        <a mat-list-item routerLink="/">Home</a>
      </mat-nav-list>
    </nav>
  `,
})
export class AppMenuPlaceholder {}
