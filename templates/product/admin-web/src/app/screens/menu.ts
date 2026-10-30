import {ChangeDetectionStrategy, Component, computed, inject} from '@angular/core';
import {MatListModule} from '@angular/material/list';
import {RouterLink, RouterLinkActive} from '@angular/router';
import {MODEL} from '../generated/model';
import {Session} from './session';

/** Menu of the signed-in role from ui.json menus. */
@Component({
  selector: 'app-menu',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatListModule, RouterLink, RouterLinkActive],
  template: `
    <nav aria-label="Меню">
      <mat-nav-list>
        @for (item of items(); track item.path) {
          <a mat-list-item [routerLink]="['/' + item.path]" routerLinkActive="active" [activated]="false">{{ item.title }}</a>
        }
        <a mat-list-item routerLink="/" (click)="session.use('')">Сменить роль</a>
      </mat-nav-list>
    </nav>
  `,
  styles: `
    .active { font-weight: 600; }
  `,
})
export class AppMenu {
  readonly session = inject(Session);
  readonly items = computed(() =>
    (MODEL.menus[this.session.role() ?? ''] ?? [])
      .filter((path) => MODEL.screens[path])
      .map((path) => ({path, title: MODEL.screens[path].title})),
  );
}
