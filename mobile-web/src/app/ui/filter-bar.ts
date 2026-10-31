import {ChangeDetectionStrategy, Component, input, output} from '@angular/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';

@Component({
  selector: 'app-filter-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatFormFieldModule, MatInputModule],
  template: `
    <mat-form-field appearance="outline" subscriptSizing="fixed">
      <mat-label>Filter</mat-label>
      <input matInput [value]="query()" (input)="onInput($event)" />
    </mat-form-field>
  `,
  styles: `
    :host { display: block; max-width: 420px; }
    mat-form-field { width: 100%; }
  `,
})
export class AppFilterBar {
  readonly query = input('');
  readonly queryChange = output<string>();

  onInput(event: Event): void {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) {
      return;
    }
    this.queryChange.emit(target.value);
  }
}
