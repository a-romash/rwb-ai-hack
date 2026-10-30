import {ChangeDetectionStrategy, Component, computed, ElementRef, inject, input, output} from '@angular/core';
import {TuiIcon} from '@taiga-ui/core';
import {PipelineItem} from './pipeline.model';

/**
 * Конвейер RWB сверху вниз: шаги Э1–Э7 и ворота качества между ними, как шаги прогона в CI.
 * Строки — кнопки с общим фокусом: стрелки вверх и вниз переключают выбранный шаг или ворота.
 */
@Component({
  selector: 'app-pipeline-timeline',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiIcon],
  host: {'(keydown)': 'onKeydown($event)'},
  template: `
    <div class="timeline" role="group" [attr.aria-label]="label()">
      @for (item of items(); track item.id) {
        <button
          type="button"
          class="row"
          [class.is-gate]="item.kind === 'gate'"
          [class.is-selected]="item.id === selected()"
          [class.is-live]="item.kind === 'stage' && item.live"
          [attr.data-key]="item.kind === 'stage' ? item.key : item.id"
          [attr.data-tone]="item.tone"
          [attr.tabindex]="item.id === focusId() ? 0 : -1"
          [attr.aria-current]="item.id === selected() ? 'true' : null"
          [attr.aria-controls]="controls()"
          [attr.aria-label]="ariaLabel(item)"
          (click)="select.emit(item.id)"
        >
          <tui-icon class="status" [icon]="item.icon" />
          @if (item.kind === 'stage') {
            <span class="code">{{ item.code }}</span>
            <span class="title">{{ item.title }}</span>
          } @else {
            <span class="code">{{ item.key }}</span>
            <span class="title">{{ item.name }}</span>
          }
          <span class="note">{{ item.statusLabel }}</span>
        </button>
      }
    </div>
  `,
  styles: `
    :host { display: block; }
    .timeline { position: relative; display: grid; gap: 2px; }
    /* Рельс через иконки статусов */
    .timeline::before {
      content: '';
      position: absolute;
      top: 22px;
      bottom: 16px;
      left: 20.25px;
      width: 1.5px;
      background: var(--p-line-strong);
    }
    .row {
      position: relative;
      display: grid;
      grid-template-columns: 16px 44px minmax(0, 1fr) auto;
      align-items: center;
      gap: 12px;
      min-height: 44px;
      padding: 0 12px;
      border: 1px solid transparent;
      border-radius: var(--p-radius-control);
      background: none;
      color: var(--p-ink);
      font: inherit;
      text-align: left;
      cursor: pointer;
      --rail-bg: var(--p-surface);
    }
    .row:hover { background: var(--p-hover); --rail-bg: var(--p-hover); }
    .row.is-selected {
      border-color: var(--p-accent);
      background: var(--p-accent-soft);
      --rail-bg: var(--p-accent-soft);
    }
    .row:focus-visible { outline-offset: 1px; }
    .status {
      position: relative;
      z-index: 1;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: var(--rail-bg);
      box-shadow: 0 0 0 4px var(--rail-bg);
      color: var(--tone, var(--p-icon));
    }
    .code {
      color: var(--p-ink-2);
      font-size: var(--p-text-xs);
      font-weight: 500;
      letter-spacing: 0;
      font-variant-numeric: tabular-nums;
    }
    .title {
      overflow: hidden;
      font-weight: 500;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .note {
      color: var(--tone-text, var(--p-ink-2));
      font-size: var(--p-text-xs);
      letter-spacing: 0;
      white-space: nowrap;
    }
    /* Ворота — подчинённые строки между шагами */
    .is-gate { min-height: 32px; }
    .is-gate .status { width: 14px; height: 14px; margin-left: 1px; box-shadow: 0 0 0 5px var(--rail-bg); }
    .is-gate .title { color: var(--p-ink-2); font-size: var(--p-text-s); font-weight: 400; }
    [data-tone='run'] { --tone: var(--p-run); --tone-text: var(--p-run-text); }
    [data-tone='wait'] { --tone: var(--p-wait); --tone-text: var(--p-wait-text); }
    [data-tone='ok'] { --tone: var(--p-ok); --tone-text: var(--p-ok-text); }
    [data-tone='fail'] { --tone: var(--p-fail); --tone-text: var(--p-fail-text); }
    .is-live .status { animation: spin 0.9s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    @media (max-width: 560px) {
      .row { grid-template-columns: 16px 40px minmax(0, 1fr); }
      .note { grid-column: 3; margin-top: -10px; padding-bottom: 8px; }
    }
  `,
})
export class PipelineTimeline {
  readonly items = input.required<PipelineItem[]>();
  readonly selected = input<string | null>(null);
  readonly label = input('Конвейер RWB');
  /** id панели, которую описывает выбранная строка. */
  readonly controls = input<string | null>(null);
  readonly select = output<string>();

  private readonly host: ElementRef<HTMLElement> = inject(ElementRef);
  protected readonly focusId = computed(() => this.selected() ?? this.items()[0]?.id ?? null);

  protected ariaLabel(item: PipelineItem): string {
    return item.kind === 'stage'
      ? `${item.code}, ${item.title}, ${item.statusLabel}`
      : `Ворота ${item.key}, ${item.name}, ${item.statusLabel}`;
  }

  protected onKeydown(event: KeyboardEvent): void {
    const items = this.items();
    const current = items.findIndex(item => item.id === this.focusId());
    if (current < 0) return;
    let next = current;
    switch (event.key) {
      case 'ArrowDown':
        next = Math.min(items.length - 1, current + 1);
        break;
      case 'ArrowUp':
        next = Math.max(0, current - 1);
        break;
      case 'Home':
        next = 0;
        break;
      case 'End':
        next = items.length - 1;
        break;
      default:
        return;
    }
    event.preventDefault();
    const item = items[next];
    this.select.emit(item.id);
    const key = item.kind === 'stage' ? item.key : item.id;
    queueMicrotask(() => this.host.nativeElement.querySelector<HTMLElement>(`[data-key="${key}"]`)?.focus());
  }
}
