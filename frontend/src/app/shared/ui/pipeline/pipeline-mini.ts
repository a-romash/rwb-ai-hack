import {ChangeDetectionStrategy, Component, computed, input} from '@angular/core';
import {plural} from '../../../core/util/text';
import {PipelineStage} from './pipeline.model';

/** Мини-прогресс конвейера: сегмент на шаг Э1–Э7, цвет сегмента — статус. */
@Component({
  selector: 'app-pipeline-mini',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {role: 'img', '[attr.aria-label]': 'summary()'},
  template: `
    @for (stage of stages(); track stage.key) {
      <i [attr.data-tone]="stage.tone" [class.is-live]="stage.live"></i>
    }
  `,
  styles: `
    :host { display: inline-flex; align-items: center; gap: 2px; flex: none; }
    i { width: 16px; height: 4px; border-radius: 2px; background: var(--p-border); }
    i[data-tone='run'] { background: var(--p-run); }
    i[data-tone='wait'] { background: var(--p-wait); }
    i[data-tone='ok'] { background: var(--p-ok); }
    i[data-tone='fail'] { background: var(--p-fail); }
    i.is-live { animation: mini-pulse 1.6s ease-in-out infinite; }
    @keyframes mini-pulse { 50% { opacity: 0.4; } }
  `,
})
export class PipelineMini {
  readonly stages = input.required<PipelineStage[]>();

  protected readonly summary = computed(() => {
    const all = this.stages();
    const done = all.filter(stage => stage.tone === 'ok').length;
    const live = all.filter(stage => stage.live).length;
    const parts = [`Готово ${done} из ${all.length} ${plural(all.length, ['шага', 'шагов', 'шагов'])} конвейера`];
    if (live) parts.push(`${live} ${plural(live, ['выполняется', 'выполняются', 'выполняются'])}`);
    return parts.join(', ');
  });
}
