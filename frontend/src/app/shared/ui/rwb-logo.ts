import {ChangeDetectionStrategy, Component} from '@angular/core';

/** Словесный знак RWB с rwb.ru. Монохромный, как на сайте компании: цвет берётся из темы. */
@Component({
  selector: 'app-rwb-logo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg viewBox="0 0 83 28" aria-hidden="true" focusable="false">
      <path
        d="M23.514 27.096h-5.318l-3.34-5.88H0v-4.222h16.722c1.925 0 3.485-1.545 3.485-3.451s-1.56-3.452-3.485-3.452H0V5.88h17.36c4.276 0 7.743 3.433 7.743 7.668 0 3.339-2.159 6.171-5.167 7.224zm23.306-5.88h-2.707l-4.227-7.47-4.23 7.47H32.95L24.266 5.88h5.314l4.723 8.335 4.722-8.335h1.72l4.722 8.334 4.722-8.334h5.314zm27.478 0h-17.36v-4.222H73.66c1.925 0 3.486-1.545 3.486-3.451s-1.56-3.451-3.486-3.451H56.938V0h5.183v5.88h12.177c4.276 0 7.743 3.433 7.743 7.668s-3.467 7.668-7.743 7.668"
      />
    </svg>
  `,
  styles: `
    :host { display: inline-flex; height: 15px; aspect-ratio: 83 / 28; flex: none; color: var(--p-ink); }
    svg { width: 100%; height: 100%; }
    path { fill: currentColor; }
  `,
})
export class RwbLogo {}
