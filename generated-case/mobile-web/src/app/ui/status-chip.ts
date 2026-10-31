import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatChipsModule} from '@angular/material/chips';

@Component({
  selector: 'app-status-chip',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatChipsModule],
  template: `
    <mat-chip-set>
      <mat-chip>{{ label() }}</mat-chip>
    </mat-chip-set>
  `,
})
export class AppStatusChip {
  readonly label = input.required<string>();
}
