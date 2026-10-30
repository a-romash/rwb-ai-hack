import {ChangeDetectionStrategy, Component} from '@angular/core';

/**
 * Словесный знак «ПОТОК»: жирная круглая монолиния со скруглёнными концами —
 * тот же приём, что у значка потока и знака RWB. Цвет берётся из темы.
 */
@Component({
  selector: 'app-potok-wordmark',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg viewBox="-5 -1 152 34" aria-hidden="true" focusable="false">
      <path d="M0 28V13a9 9 0 0 1 18 0v15" />
      <circle cx="40.5" cy="16" r="12" />
      <path d="M62 4h20M72 4v24" />
      <circle cx="103.5" cy="16" r="12" />
      <path d="M126 4v24M142 4l-10.5 12 10.5 12M126 16h5.5" />
    </svg>
  `,
  styles: `
    :host { display: inline-flex; height: 15px; aspect-ratio: 152 / 34; flex: none; color: var(--p-ink); }
    svg { width: 100%; height: 100%; overflow: visible; }
    path, circle { fill: none; stroke: currentColor; stroke-width: 7; stroke-linecap: round; stroke-linejoin: round; }
  `,
})
export class PotokWordmark {}
