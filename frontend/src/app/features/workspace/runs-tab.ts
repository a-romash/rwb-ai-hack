import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {TuiButton, TuiIcon} from '@taiga-ui/core';
import {AGENTS} from '../../core/pipeline/agents.catalog';
import {Clock} from '../../core/state/clock.service';
import {Confirm} from '../../shared/ui/confirm-dialog';
import {JobCard} from './job-card';
import {RunLauncher} from './run-launcher';
import {WorkspaceStore} from './workspace.store';

/** Вкладка «Запуски»: история задач агентов этого проекта с живыми статусами. */
@Component({
  selector: 'app-runs-tab',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiButton, TuiIcon, JobCard],
  template: `
    <div class="bar">
      <div>
        <h2 class="section-title">Запуски агентов</h2>
        <p class="subtle">История хранится в этом браузере: у API пока нет списка задач проекта. Статусы приходят с сервера.</p>
      </div>
      <button tuiButton type="button" size="s" appearance="secondary" iconStart="@tui.play" (click)="launch()">Запустить агента</button>
    </div>

    @for (job of store.runs(); track job.id) {
      <app-job-card [job]="job" [now]="clock.now()" (refresh)="store.refresh($event)" (remove)="remove($event)" />
    } @empty {
      <div class="empty panel">
        <span class="empty-icon" aria-hidden="true"><tui-icon icon="@tui.square-terminal" /></span>
        <h3 class="empty-title">Запусков пока нет</h3>
        <p class="empty-text">
          Начните с аналитика: он разберёт требования, найдёт пробелы и перечислит допущения. Результат и статус появятся здесь
          и на линии этапов.
        </p>
        <button tuiButton type="button" size="m" [iconStart]="analyst.icon" (click)="launch('business_analysis', 'analyst')">
          Запустить {{ analyst.accusative }}
        </button>
      </div>
    }
  `,
  styles: `
    :host { display: grid; gap: 12px; }
    .bar { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 12px 24px; margin-bottom: 4px; }
    .subtle { margin-top: 2px; max-width: 68ch; }
    .empty { display: grid; justify-items: center; gap: 6px; padding: 48px 24px 40px; text-align: center; }
    .empty-icon {
      display: grid;
      place-items: center;
      width: 40px;
      height: 40px;
      margin-bottom: 10px;
      border: 1px solid var(--p-border);
      border-radius: var(--p-radius-control);
      background: var(--p-surface-2);
      tui-icon { width: 20px; height: 20px; color: var(--p-ink-2); }
    }
    .empty-title { font-size: var(--p-text-xl); line-height: 1.75rem; letter-spacing: -0.017em; }
    .empty-text { max-width: 54ch; margin-bottom: 18px; color: var(--p-ink-2); line-height: 1.25rem; }
  `,
})
export class RunsTab {
  protected readonly store = inject(WorkspaceStore);
  protected readonly clock = inject(Clock);
  private readonly launcher = inject(RunLauncher);
  private readonly confirm = inject(Confirm);
  protected readonly analyst = AGENTS.analyst;

  protected launch(stageKey: string | null = null, agent: string | null = null): void {
    this.launcher.open(stageKey, agent);
  }

  protected remove(jobId: string): void {
    this.confirm
      .ask({
        title: 'Убрать запуск из истории?',
        text: 'Запись исчезнет из этой Студии. Задача в очереди не отменяется.',
        confirm: 'Убрать',
        cancel: 'Оставить',
        danger: true,
      })
      .subscribe(yes => {
        if (yes) this.store.remove(jobId);
      });
  }
}
