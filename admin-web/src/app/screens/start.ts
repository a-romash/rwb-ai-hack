import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {Router} from '@angular/router';
import {MODEL} from '../generated/model';
import {AppPage} from '../ui/page';
import {Session} from './session';

/** Role picker; a chosen role goes straight to its home screen from ui.json. */
@Component({
  selector: 'app-start',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatButtonModule, AppPage],
  template: `
    <app-page [title]="title">
      <p class="lead">Демо-вход по роли: выберите, кем открыть приложение.</p>
      <div class="roles">
        @for (role of roles; track role.id) {
          <button mat-stroked-button type="button" [attr.data-testid]="'start.role-' + role.id" (click)="choose(role.id)">
            {{ role.name }}
          </button>
        }
      </div>
    </app-page>
  `,
  styles: `
    .lead { margin: 0; }
    .roles { display: flex; flex-wrap: wrap; gap: 12px; }
  `,
})
export class Start {
  private readonly router = inject(Router);
  private readonly session = inject(Session);
  readonly title = MODEL.title || 'Вход';
  readonly roles = Object.entries(MODEL.roles)
    .filter(([id]) => MODEL.home[id] || MODEL.menus[id]?.length)
    .map(([id, name]) => ({id, name}));

  constructor() {
    const role = this.session.role();
    if (role && this.home(role)) {
      void this.router.navigate(['/' + this.home(role)], {replaceUrl: true});
    }
  }

  choose(role: string): void {
    this.session.use(role);
    const home = this.home(role);
    if (home) {
      void this.router.navigate(['/' + home]);
    }
  }

  private home(role: string): string | undefined {
    return MODEL.home[role] ?? MODEL.menus[role]?.[0];
  }
}
