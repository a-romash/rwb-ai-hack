import {ChangeDetectionStrategy, Component, computed, input, output} from '@angular/core';
import {TuiButton, TuiIcon} from '@taiga-ui/core';
import {AUTONOMY, GATES, stageInfo} from '../../core/pipeline/stages.catalog';
import {PipelineGate} from '../../shared/ui/pipeline/pipeline.model';
import {StatusChip} from '../../shared/ui/status-chip';

/** Ворота качества: что проверяется, кто решает и что будет, если проверка не прошла. */
@Component({
  selector: 'app-gate-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiButton, TuiIcon, StatusChip],
  template: `
    @let g = gate();
    <header>
      <p class="kicker">
        <span class="code">{{ g.key }}</span>
        <span>Ворота качества после шага {{ after()?.code }} «{{ after()?.title }}»</span>
      </p>
      <div class="title-row">
        <h2 class="title">{{ g.name }}</h2>
        <app-status-chip [tone]="g.tone" [label]="g.statusLabel" />
      </div>
    </header>

    <dl class="io">
      <div>
        <dt>Что проверяется</dt>
        <dd>{{ info().check }}</dd>
      </div>
      <div>
        <dt>Кто решает</dt>
        <dd>{{ info().decider }}</dd>
      </div>
      <div>
        <dt>Если не прошло</dt>
        <dd>{{ info().onFail }}</dd>
      </div>
    </dl>

    @if (g.result; as result) {
      <section class="findings" aria-label="Находки проверки">
        @for (finding of findings(); track $index) {
          <p class="finding" [attr.data-severity]="finding.severity">
            <span class="finding-code">{{ finding.code }}</span>
            <span class="finding-path">{{ finding.path }}</span>
            <span class="finding-text">{{ finding.message }}</span>
          </p>
        } @empty {
          <p class="note"><tui-icon icon="@tui.circle-check" /><span>Замечаний нет.</span></p>
        }
        @if (result.findings.length > findings().length) {
          <p class="more">И ещё {{ result.findings.length - findings().length }} — в отчёте шага.</p>
        }
      </section>
    } @else {
      <p class="note">
        <tui-icon icon="@tui.info" />
        <span>
          Результат появится, когда прогон конвейера дойдёт до этих ворот. В режиме A2 «{{ autonomy.name }}» человек не участвует,
          вопросы закрываются ответами по умолчанию.
        </span>
      </p>
    }

    @if (g.waiting) {
      <footer class="decision">
        <button tuiButton type="button" size="s" iconStart="@tui.check" (click)="decide.emit('approve')">Принять и продолжить</button>
        <button tuiButton type="button" size="s" appearance="flat" iconStart="@tui.undo-2" (click)="decide.emit('reject')">Вернуть на доработку</button>
      </footer>
    }

    <button type="button" class="back" (click)="openStage.emit(g.stageKey)">
      <tui-icon icon="@tui.arrow-left" />
      К шагу «{{ after()?.title }}»
    </button>
  `,
  styleUrl: './station-panel.less',
  styles: `
    .note {
      display: grid;
      grid-template-columns: 16px minmax(0, 1fr);
      gap: 10px;
      padding: 12px 14px;
      border: 1px solid var(--p-line);
      border-radius: var(--p-radius-control);
      background: var(--p-surface-2);
      color: var(--p-ink-2);
      font-size: var(--p-text-s);
      line-height: 1.25rem;
    }
    .note tui-icon { width: 16px; height: 16px; margin-top: 2px; color: var(--p-icon); }
    .back {
      display: inline-flex;
      align-items: center;
      justify-self: start;
      gap: 6px;
      padding: 0;
      border: 0;
      background: none;
      color: var(--p-accent-text);
      font: inherit;
      font-weight: 500;
      cursor: pointer;
    }
    .back tui-icon { width: 16px; height: 16px; }
    .findings { display: grid; gap: 6px; }
    .finding {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      gap: 2px 10px;
      padding: 8px 12px;
      border-left: 2px solid var(--p-wait);
      background: var(--p-surface-2);
      font-size: var(--p-text-s);
    }
    .finding[data-severity='error'] { border-left-color: var(--p-fail); }
    .finding-code { font-family: var(--p-font-code); font-size: var(--p-text-xs); font-weight: 600; }
    .finding-path { color: var(--p-ink-2); font-size: var(--p-text-xs); overflow-wrap: anywhere; }
    .finding-text { grid-column: 1 / -1; }
    .more { color: var(--p-ink-2); font-size: var(--p-text-xs); }
    .decision { display: flex; flex-wrap: wrap; gap: 8px; }
    .back { text-decoration: underline; text-decoration-color: var(--p-line-strong); text-underline-offset: 3px; }
    .back:hover { text-decoration-color: currentColor; }
  `,
})
export class GatePanel {
  readonly gate = input.required<PipelineGate>();
  readonly openStage = output<string>();
  readonly decide = output<'approve' | 'reject'>();

  /** Сначала ошибки, затем предупреждения; длинный список обрезан — целиком он в отчёте шага. */
  protected readonly findings = computed(() =>
    [...(this.gate().result?.findings ?? [])].sort((a, b) => (a.severity === b.severity ? 0 : a.severity === 'error' ? -1 : 1)).slice(0, 12),
  );

  protected readonly info = computed(() => GATES[this.gate().key]);
  protected readonly after = computed(() => stageInfo(this.gate().stageKey));
  protected readonly autonomy = AUTONOMY.A2;
}
