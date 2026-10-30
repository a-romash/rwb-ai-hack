import {ChangeDetectionStrategy, Component} from '@angular/core';

/** Знак «Поток»: линия, которая расходится на ветки, — как граф этапов. Монохромный, цвета темы. */
@Component({
  selector: 'app-brand-mark',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <path d="M6 16h5c3 0 3.5-6 7-6h8M11 16c3 0 3.5 6 7 6h8M6 16h20" class="flow" />
      <circle cx="6" cy="16" r="2.4" class="dot" />
    </svg>
  `,
  styles: `
    :host {
      display: inline-flex;
      width: 24px;
      height: 24px;
      flex: none;
      border-radius: 6px;
      background: var(--p-primary);
    }
    svg { width: 100%; height: 100%; }
    .flow { fill: none; stroke: var(--p-on-primary); stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; }
    .dot { fill: var(--p-on-primary); }
  `,
})
export class BrandMark {}
