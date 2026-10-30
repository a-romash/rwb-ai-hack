import {ChangeDetectionStrategy, Component} from '@angular/core';
import {TuiIcon} from '@taiga-ui/core';
import {GATES, STAGE_CATALOG} from '../../../core/pipeline/stages.catalog';

/** Конвейер RWB без проекта: что произойдёт с требованиями. Шаги по порядку и их ворота. */
@Component({
  selector: 'app-pipeline-chain',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiIcon],
  template: `
    <ol class="chain">
      @for (stage of stages; track stage.key; let i = $index) {
        <li class="step">
          <span class="head">
            <span class="index num" aria-hidden="true">{{ i + 1 }}</span>
            <span class="code">{{ stage.code }}</span>
          </span>
          <span class="title">{{ stage.title }}</span>
          @if (stage.gates.length) {
            <span class="gates">
              @for (gate of stage.gates; track gate) {
                <span class="gate"><tui-icon icon="@tui.shield" />{{ gate }} {{ gates[gate].name }}</span>
              }
            </span>
          } @else {
            <span class="gates is-empty">Без ворот</span>
          }
        </li>
      }
    </ol>
  `,
  styles: `
    :host { display: block; }
    .chain {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .step {
      display: grid;
      gap: 4px;
      padding: 12px 14px;
      border: 1px solid var(--p-border);
      border-radius: var(--p-radius-control);
      background: var(--p-surface);
    }
    .head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
    .index {
      display: grid;
      place-items: center;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: var(--p-accent-soft);
      color: var(--p-accent-text);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0;
    }
    .code { color: var(--p-ink-2); font-size: var(--p-text-xs); font-weight: 500; letter-spacing: 0; }
    .title { font-weight: 500; }
    .gates { display: flex; flex-wrap: wrap; gap: 4px 10px; color: var(--p-ink-2); font-size: var(--p-text-xs); letter-spacing: 0; }
    .gate { display: inline-flex; align-items: center; gap: 4px; }
    .gate tui-icon { width: 12px; height: 12px; color: var(--p-icon); }
    @media (max-width: 960px) { .chain { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  `,
})
export class PipelineChain {
  protected readonly stages = STAGE_CATALOG;
  protected readonly gates = GATES;
}
