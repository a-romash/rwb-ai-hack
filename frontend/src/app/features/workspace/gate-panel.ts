import {ChangeDetectionStrategy, Component, computed, input, output} from '@angular/core';
import {TuiIcon} from '@taiga-ui/core';
import {AUTONOMY, GATES, stageInfo} from '../../core/pipeline/stages.catalog';
import {PipelineGate} from '../../shared/ui/pipeline/pipeline.model';
import {StatusChip} from '../../shared/ui/status-chip';

/** Ворота качества: что проверяется, кто решает и что будет, если проверка не прошла. */
@Component({
  selector: 'app-gate-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiIcon, StatusChip],
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

    <p class="note">
      <tui-icon icon="@tui.info" />
      <span>
        Результат ворот покажет прогон конвейера целиком. Режим по умолчанию — A2 «{{ autonomy.name }}»: человек не участвует,
        вопросы закрываются ответами по умолчанию.
      </span>
    </p>

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
    .back { text-decoration: underline; text-decoration-color: var(--p-line-strong); text-underline-offset: 3px; }
    .back:hover { text-decoration-color: currentColor; }
  `,
})
export class GatePanel {
  readonly gate = input.required<PipelineGate>();
  readonly openStage = output<string>();

  protected readonly info = computed(() => GATES[this.gate().key]);
  protected readonly after = computed(() => stageInfo(this.gate().stageKey));
  protected readonly autonomy = AUTONOMY.A2;
}
