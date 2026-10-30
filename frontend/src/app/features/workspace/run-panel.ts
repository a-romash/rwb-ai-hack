import {ChangeDetectionStrategy, Component, computed, inject, signal} from '@angular/core';
import {TuiButton} from '@taiga-ui/core';
import {Autonomy} from '../../core/api/api.types';
import {readableError} from '../../core/api/errors';
import {AUTONOMY} from '../../core/pipeline/stages.catalog';
import {Clock} from '../../core/state/clock.service';
import {ToastService} from '../../core/state/toast.service';
import {formatNumber} from '../../core/util/text';
import {RelTimePipe} from '../../shared/ui/rel-time.pipe';
import {StatusChip} from '../../shared/ui/status-chip';
import {WorkspaceStore} from './workspace.store';

/** Прогон конвейера целиком: запуск, статус и бюджет, вопросы аналитику, артефакты. */
@Component({
  selector: 'app-run-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiButton, StatusChip, RelTimePipe],
  template: `
    @let run = store.pipelineRun();
    <header class="head">
      <div>
        <h2 class="title">Прогон конвейера</h2>
        @if (run) {
          <p class="meta">
            <span>Запущен {{ run.created_at | relTime: clock.now() }}</span>
            <span>Режим {{ run.autonomy }} «{{ autonomyName(run.autonomy) }}»</span>
            <span class="num">{{ minutes() }}</span>
            <span class="num">{{ tokens() }}</span>
          </p>
        } @else {
          <p class="meta">Все восемь шагов подряд: требования → спецификация → экраны → код → проверки → отчёт.</p>
        }
      </div>
      @if (run && store.pipelineView(); as view) {
        <app-status-chip [tone]="view.tone" [label]="view.label" [live]="view.live" />
      }
    </header>

    <div class="controls">
      <label class="field">
        <span>Автономность</span>
        <select [value]="autonomy()" (change)="autonomy.set($any($event.target).value)" [disabled]="busy()">
          @for (mode of modes; track mode.key) {
            <option [value]="mode.key">{{ mode.key }} — {{ mode.name }}</option>
          }
        </select>
      </label>
      <button tuiButton type="button" size="s" iconStart="@tui.play" [disabled]="busy() || store.pipelineView()?.live" (click)="start()">
        {{ run ? 'Запустить заново' : 'Запустить конвейер' }}
      </button>
      @if (store.pipelineView()?.live) {
        <button tuiButton type="button" size="s" appearance="flat" iconStart="@tui.square" [disabled]="busy()" (click)="cancel()">Остановить</button>
      }
    </div>

    @if (run?.prototype_url; as prototypeUrl) {
      <section class="prototype" aria-label="Результат прогона" aria-live="polite">
        <a tuiButton appearance="secondary" size="s" iconStart="@tui.external-link" [href]="prototypeUrl" target="_blank" rel="noopener noreferrer">Открыть прототип</a>
        <p class="why">Доступен до следующего запуска конвейера</p>
      </section>
    }

    <section class="attachments" aria-label="Данные к требованиям">
      <div class="attach-head">
        <p class="section-title">Данные к требованиям</p>
        <label class="upload" [class.disabled]="uploading()">
          <input
            type="file"
            multiple
            accept=".json,.geojson,.csv,.txt,.md,.markdown,.docx,.pdf"
            [disabled]="uploading()"
            (change)="upload($any($event.target))"
            data-testid="run.attach"
          />
          {{ uploading() ? 'Загружаю…' : 'Приложить файлы' }}
        </label>
      </div>
      @if (store.attachments().length) {
        <ul>
          @for (file of store.attachments(); track file.name) {
            <li><span class="name">{{ file.name }}</span><span class="path">{{ size(file.size) }}</span></li>
          }
        </ul>
      } @else {
        <p class="why">JSON, CSV, GeoJSON, DOCX или PDF. Шаг анализа профилирует их и не отправляет модели сырые данные. Файлы получит следующий прогон.</p>
      }
    </section>

    @if (run?.questions?.length) {
      <form class="questions" aria-label="Вопросы аналитику" (submit)="$event.preventDefault(); answer()">
        <p class="section-title">Вопросы аналитику</p>
        @for (question of run!.questions; track question.id) {
          <fieldset>
            <legend>{{ question.text }}</legend>
            <p class="why">{{ question.why }}</p>
            @for (option of question.options; track option) {
              <label class="option">
                <input
                  type="radio"
                  [name]="question.id"
                  [value]="option"
                  [checked]="(answers()[question.id] ?? question.default) === option"
                  (change)="pick(question.id, option)"
                />
                {{ option }}@if (option === question.default) {<span class="muted"> · по умолчанию</span>}
              </label>
            }
          </fieldset>
        }
        <button tuiButton type="submit" size="s" [disabled]="busy()">Ответить и продолжить</button>
      </form>
    }

    @if (store.artifacts().length) {
      <section class="artifacts" aria-label="Артефакты прогона">
        <p class="section-title">Артефакты</p>
        <ul>
          @for (artifact of store.artifacts(); track artifact.name) {
            <li>
              @if (artifact.kind === 'dir') {
                <span class="name">{{ artifact.name }}</span>
              } @else {
                <a class="name" [href]="store.fileUrl(artifact.path)" target="_blank" rel="noopener">{{ artifact.name }}</a>
              }
              <span class="path">{{ artifact.path }}</span>
            </li>
          }
        </ul>
      </section>
    }
  `,
  styles: `
    :host { display: grid; gap: 14px; padding: 16px; }
    .head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
    .title { font-size: var(--p-text-m); line-height: 1.25rem; font-weight: 600; }
    .meta { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: 4px; color: var(--p-ink-2); font-size: var(--p-text-xs); line-height: 1rem; }
    .controls { display: flex; flex-wrap: wrap; align-items: end; gap: 8px; }
    .prototype { display: grid; justify-items: start; gap: 8px; }
    .field { display: grid; gap: 4px; color: var(--p-ink-2); font-size: var(--p-text-xs); }
    select {
      min-height: 32px;
      padding: 0 8px;
      border: 1px solid var(--p-line-strong);
      border-radius: var(--p-radius-control);
      background: var(--p-surface);
      color: var(--p-ink);
      font: inherit;
      font-size: var(--p-text-s);
    }
    select:focus-visible, input:focus-visible { outline: 2px solid var(--p-focus); outline-offset: 2px; }
    .section-title { font-weight: 600; }
    .questions { display: grid; gap: 12px; padding: 12px 14px; border: 1px solid var(--p-line); border-radius: var(--p-radius-control); background: var(--p-surface-2); }
    fieldset { display: grid; gap: 4px; margin: 0; padding: 0; border: 0; }
    legend { font-weight: 500; }
    .why, .muted { color: var(--p-ink-2); font-size: var(--p-text-xs); }
    .option { display: flex; align-items: center; gap: 8px; }
    .attachments { display: grid; gap: 6px; }
    .attach-head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; }
    .attachments ul { display: grid; gap: 4px; margin: 0; padding: 0; list-style: none; }
    .attachments li { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; }
    .upload {
      position: relative;
      display: inline-flex;
      align-items: center;
      min-height: 32px;
      padding: 0 12px;
      border: 1px solid var(--p-line-strong);
      border-radius: var(--p-radius-control);
      color: var(--p-ink);
      font-size: var(--p-text-s);
      cursor: pointer;
    }
    .upload:focus-within { outline: 2px solid var(--p-focus); outline-offset: 2px; }
    .upload.disabled { opacity: .6; cursor: progress; }
    .upload input { position: absolute; inset: 0; opacity: 0; cursor: inherit; }
    .artifacts ul { display: grid; gap: 6px; margin: 8px 0 0; padding: 0; list-style: none; }
    .artifacts li { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; }
    .name { font-weight: 500; color: var(--p-accent-text); }
    .path { color: var(--p-ink-2); font-size: var(--p-text-xs); font-family: var(--p-font-code); overflow-wrap: anywhere; }
  `,
})
export class RunPanel {
  protected readonly store = inject(WorkspaceStore);
  protected readonly clock = inject(Clock);
  private readonly toasts = inject(ToastService);

  protected readonly modes = (['A2', 'A1', 'A0'] as const).map(key => ({key, name: AUTONOMY[key].name}));
  protected readonly autonomy = signal<Autonomy>('A2');
  protected readonly busy = signal(false);
  protected readonly answers = signal<Record<string, string | undefined>>({});
  protected readonly uploading = signal(false);

  protected readonly minutes = computed(() => {
    const budget = this.store.pipelineRun()?.budget;
    return budget ? `${formatNumber(Math.round(budget.minutes_used))} из ${formatNumber(budget.minutes_limit)} мин` : '';
  });
  protected readonly tokens = computed(() => {
    const budget = this.store.pipelineRun()?.budget;
    if (!budget) return '';
    const used = budget.tokens_used === null ? 'расход неизвестен' : formatNumber(budget.tokens_used);
    return `${used} из ${formatNumber(budget.tokens_limit)} токенов`;
  });

  protected size(bytes: number): string {
    return bytes < 1024 * 1024 ? `${formatNumber(Math.ceil(bytes / 1024))} КБ` : `${formatNumber(Math.round(bytes / 1024 / 102.4) / 10)} МБ`;
  }

  /** Файлы уходят по одному: при ошибке остальные уже загружены, а тост называет проблемный файл. */
  protected upload(input: HTMLInputElement): void {
    const files = Array.from(input.files ?? []);
    input.value = '';
    const next = (): void => {
      const file = files.shift();
      if (!file) {
        this.uploading.set(false);
        return;
      }
      this.store.attach(file).subscribe({
        next: () => {
          this.toasts.success(`Файл ${file.name} приложен`);
          next();
        },
        error: error => {
          this.uploading.set(false);
          // The API explains a rejected name, format or size in detail; the generic 422 hint is about projects.
          const detail = error?.error?.detail;
          this.toasts.error(`Не удалось приложить ${file.name}`, typeof detail === 'string' ? detail : readableError(error, 'job').hint);
        },
      });
    };
    if (files.length) {
      this.uploading.set(true);
      next();
    }
  }

  protected autonomyName(key: Autonomy): string {
    return AUTONOMY[key].name;
  }

  protected pick(id: string, option: string): void {
    this.answers.update(answers => ({...answers, [id]: option}));
  }

  protected start(): void {
    this.act(this.store.startRun(this.autonomy(), {tokens: 1_500_000, minutes: 60}), 'Конвейер запущен');
  }

  protected cancel(): void {
    this.act(this.store.cancelRun(), 'Прогон остановлен');
  }

  protected answer(): void {
    const questions = this.store.pipelineRun()?.questions ?? [];
    const answers = Object.fromEntries(questions.map(q => [q.id, this.answers()[q.id] ?? q.default]));
    this.act(this.store.answer(answers), 'Ответы приняты');
  }

  private act(request: ReturnType<WorkspaceStore['cancelRun']>, done: string): void {
    this.busy.set(true);
    request.subscribe({
      next: () => {
        this.busy.set(false);
        this.toasts.success(done);
      },
      error: error => {
        this.busy.set(false);
        const readable = readableError(error, 'job');
        this.toasts.error(readable.title, readable.hint);
      },
    });
  }
}
