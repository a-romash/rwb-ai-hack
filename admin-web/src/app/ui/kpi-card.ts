import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatCardModule} from '@angular/material/card';

@Component({
  selector: 'app-kpi-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatCardModule],
  template: `
    <mat-card>
      <mat-card-header>
        <mat-card-title>{{ value() }}</mat-card-title>
        <mat-card-subtitle>{{ label() }}</mat-card-subtitle>
      </mat-card-header>
    </mat-card>
  `,
})
export class AppKpiCard {
  readonly label = input.required<string>();
  readonly value = input.required<string>();
}
