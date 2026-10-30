import {ChangeDetectionStrategy, Component, computed, input} from '@angular/core';
import {TuiIcon} from '@taiga-ui/core';
import {analyzeRequirements} from '../../core/util/requirements-insights';

/** Что уже описано в требованиях: подсказка до запуска анализа. */
@Component({
  selector: 'app-requirements-insights',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiIcon],
  template: `
    <div class="head">
      <h2 class="title">Что уже описано</h2>
      <span class="score num" [attr.aria-label]="'Описано ' + covered() + ' из ' + aspects().length">{{ covered() }} из {{ aspects().length }}</span>
    </div>
    <div class="meter" aria-hidden="true">
      @for (aspect of aspects(); track aspect.key) {
        <i [class.on]="aspect.present"></i>
      }
    </div>
    <ul class="list">
      @for (aspect of aspects(); track aspect.key) {
        <li [class.present]="aspect.present">
          <tui-icon class="mark" [icon]="aspect.present ? '@tui.circle-check' : '@tui.circle-dashed'" />
          <span class="text">
            <span class="label">{{ aspect.label }}<span class="visually-hidden">{{ aspect.present ? ' — упомянуто' : ' — не найдено' }}</span></span>
            @if (!aspect.present) {
              <span class="tip">{{ aspect.tip }}</span>
            }
          </span>
        </li>
      }
    </ul>
    <p class="note">Подсказка по ключевым словам. Полный разбор с вопросами сделает этап бизнес-анализа.</p>
  `,
  styles: `
    :host { display: block; }
    .head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
    .title { font-size: var(--p-text-m); line-height: 1.25rem; font-weight: 600; }
    .score { color: var(--p-ink-2); font-size: var(--p-text-xs); font-weight: 500; letter-spacing: 0; }
    .meter { display: grid; grid-template-columns: repeat(6, 1fr); gap: 2px; margin: 10px 0 14px; }
    .meter i { height: 4px; border-radius: 2px; background: var(--p-border); transition: background-color var(--p-base) var(--p-ease); }
    .meter i.on { background: var(--p-ok); }
    .list { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }
    li { display: grid; grid-template-columns: 16px 1fr; gap: 10px; align-items: start; }
    .mark { width: 16px; height: 16px; margin-top: 2px; color: var(--p-icon); }
    .present .mark { color: var(--p-ok); }
    .text { display: grid; gap: 2px; }
    .label { font-weight: 500; color: var(--p-ink-2); }
    .present .label { color: var(--p-ink); }
    .tip { color: var(--p-ink-2); font-size: var(--p-text-s); line-height: 1.125rem; }
    .note { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--p-line); color: var(--p-ink-2); font-size: var(--p-text-xs); line-height: 1rem; letter-spacing: 0; }
  `,
})
export class RequirementsInsights {
  readonly text = input('');

  protected readonly aspects = computed(() => analyzeRequirements(this.text()));
  protected readonly covered = computed(() => this.aspects().filter(aspect => aspect.present).length);
}
