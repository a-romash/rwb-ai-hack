import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatCardModule} from '@angular/material/card';

@Component({
  selector: 'app-empty-state',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatCardModule],
  template: `
    <mat-card class="empty">
      <mat-card-header>
        <mat-card-title>{{ title() }}</mat-card-title>
      </mat-card-header>
      <mat-card-content>
        @if (message()) {
          <p>{{ message() }}</p>
        }
        <ng-content />
      </mat-card-content>
    </mat-card>
  `,
  styles: `
    .empty { text-align: center; }
    p { margin: 8px 0 0; }
  `,
})
export class AppEmptyState {
  readonly title = input.required<string>();
  readonly message = input('');
}
