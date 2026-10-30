import {ChangeDetectionStrategy, Component, computed, input} from '@angular/core';
import {PHASES} from '../../../core/pipeline/stages.catalog';
import {plural} from '../../../core/util/text';
import {byPlace, FlowStation} from './flow.model';

/** Мини-прогресс этапов: сегмент на этап, сгруппированные по фазам. Цвет сегмента — статус. */
@Component({
  selector: 'app-flow-mini',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {role: 'img', '[attr.aria-label]': 'summary()'},
  template: `
    @for (group of groups(); track group.key) {
      <span class="group">
        @for (station of group.stations; track station.key) {
          <i [attr.data-tone]="station.tone" [class.is-live]="station.live"></i>
        }
      </span>
    }
  `,
  styles: `
    :host { display: inline-flex; align-items: center; gap: 6px; flex: none; }
    .group { display: inline-flex; gap: 2px; }
    i { width: 14px; height: 4px; border-radius: 2px; background: var(--p-border); }
    i[data-tone='run'] { background: var(--p-run); }
    i[data-tone='wait'] { background: var(--p-wait); }
    i[data-tone='ok'] { background: var(--p-ok); }
    i[data-tone='fail'] { background: var(--p-fail); }
    i.is-live { animation: mini-pulse 1.6s ease-in-out infinite; }
    @keyframes mini-pulse { 50% { opacity: 0.4; } }
  `,
})
export class FlowMini {
  readonly stations = input.required<FlowStation[]>();

  protected readonly groups = computed(() => {
    const ordered = [...this.stations()].sort(byPlace);
    return PHASES.map(phase => ({key: phase.key, stations: ordered.filter(station => station.phase === phase.key)})).filter(
      group => group.stations.length,
    );
  });

  protected readonly summary = computed(() => {
    const all = this.stations();
    const done = all.filter(station => station.tone === 'ok').length;
    const live = all.filter(station => station.live).length;
    const parts = [`Готово ${done} из ${all.length} ${plural(all.length, ['этапа', 'этапов', 'этапов'])}`];
    if (live) parts.push(`${live} ${plural(live, ['выполняется', 'выполняются', 'выполняются'])}`);
    return parts.join(', ');
  });
}
