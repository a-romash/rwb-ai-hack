import {ChangeDetectionStrategy, Component, computed, input} from '@angular/core';
import {TuiIcon} from '@taiga-ui/core';
import {Tone, toneIcon} from '../../core/pipeline/status';

/** Статус одной строкой: иконка и слово, без цветной подложки. Пока процесс идёт, иконка вращается. */
@Component({
  selector: 'app-status-chip',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiIcon],
  host: {'[attr.data-tone]': 'tone()', '[class.is-live]': 'live()', '[class.is-quiet]': 'quiet()'},
  template: `<tui-icon class="icon" [icon]="icon()" /><span>{{ label() }}</span>`,
  styles: `
    :host {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: var(--chip-text);
      font-size: var(--p-text-s);
      line-height: 1.125rem;
      font-weight: 500;
      letter-spacing: -0.003em;
      white-space: nowrap;
      --chip-icon: var(--p-icon);
      --chip-text: var(--p-idle-text);
    }
    :host(.is-quiet) { font-size: var(--p-text-xs); line-height: 1rem; letter-spacing: 0; }
    :host([data-tone='run']) { --chip-icon: var(--p-run); --chip-text: var(--p-run-text); }
    :host([data-tone='wait']) { --chip-icon: var(--p-wait); --chip-text: var(--p-wait-text); }
    :host([data-tone='ok']) { --chip-icon: var(--p-ok); --chip-text: var(--p-ok-text); }
    :host([data-tone='fail']) { --chip-icon: var(--p-fail); --chip-text: var(--p-fail-text); }
    .icon { width: 16px; height: 16px; flex: none; color: var(--chip-icon); }
    :host(.is-quiet) .icon { width: 14px; height: 14px; }
    :host(.is-live) .icon { animation: chip-spin 0.9s linear infinite; }
    @keyframes chip-spin { to { transform: rotate(360deg); } }
  `,
})
export class StatusChip {
  readonly tone = input<Tone>('idle');
  readonly label = input.required<string>();
  readonly live = input(false);
  /** Мельче — внутри плотных строк. */
  readonly quiet = input(false);

  protected readonly icon = computed(() => toneIcon(this.tone(), this.live()));
}
