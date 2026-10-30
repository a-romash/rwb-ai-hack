import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {RouterLink} from '@angular/router';
import {TuiButton, TuiIcon} from '@taiga-ui/core';
import {ShellService} from '../../core/state/shell.service';

@Component({
  selector: 'app-not-found-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, TuiButton, TuiIcon],
  template: `
    <section class="page">
      <div class="empty panel">
        <span class="empty-icon" aria-hidden="true"><tui-icon icon="@tui.compass" /></span>
        <p class="code">Ошибка 404</p>
        <h1 class="empty-title">Такой страницы нет</h1>
        <p class="empty-text">Ссылка устарела или в адресе опечатка. Все проекты — в списке.</p>
        <a tuiButton size="m" iconStart="@tui.layout-list" routerLink="/projects" class="cta">К проектам</a>
      </div>
    </section>
  `,
  styles: `
    .empty { display: grid; justify-items: center; gap: 6px; padding: 56px 24px 48px; text-align: center; }
    .empty-icon {
      display: grid;
      place-items: center;
      width: 40px;
      height: 40px;
      margin-bottom: 10px;
      border: 1px solid var(--p-border);
      border-radius: var(--p-radius-control);
      background: var(--p-surface-2);
    }
    .empty-icon tui-icon { width: 20px; height: 20px; color: var(--p-ink-2); }
    .code { color: var(--p-ink-2); font-size: var(--p-text-xs); font-weight: 500; letter-spacing: 0; }
    .empty-title { font-size: var(--p-text-xl); line-height: 1.75rem; letter-spacing: -0.017em; }
    .empty-text { max-width: 48ch; color: var(--p-ink-2); }
    .cta { margin-top: 18px; }
  `,
})
export class NotFoundPage {
  constructor() {
    const shell = inject(ShellService);
    shell.crumbs.set([]);
    shell.projectId.set(null);
  }
}
