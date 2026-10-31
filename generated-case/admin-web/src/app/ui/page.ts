import {ChangeDetectionStrategy, Component, input} from '@angular/core';

@Component({
  selector: 'app-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="page">
      <header>
        <h1>{{ title() }}</h1>
        <div class="actions">
          <ng-content select="[actions]" />
        </div>
      </header>
      <div class="body">
        <ng-content />
      </div>
    </section>
  `,
  styles: `
    :host { display: block; }
    .page { display: grid; gap: 16px; padding: 24px; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
    h1 { margin: 0; font-size: 1.5rem; font-weight: 500; }
    .actions { display: flex; gap: 8px; }
    .body { display: grid; gap: 16px; }
  `,
})
export class AppPage {
  readonly title = input.required<string>();
}
