import {ChangeDetectionStrategy, Component, input, output} from '@angular/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';

@Component({
  selector: 'app-form-field',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatFormFieldModule, MatInputModule],
  template: `
    <mat-form-field appearance="outline" subscriptSizing="fixed">
      <mat-label>{{ label() }}</mat-label>
      <input matInput [value]="value()" (input)="onInput($event)" />
      @if (hint()) {
        <mat-hint>{{ hint() }}</mat-hint>
      }
    </mat-form-field>
  `,
  styles: `
    :host { display: block; max-width: 420px; }
    mat-form-field { width: 100%; }
  `,
})
export class AppFormField {
  readonly label = input.required<string>();
  readonly hint = input('');
  readonly value = input('');
  readonly valueChange = output<string>();

  onInput(event: Event): void {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) {
      return;
    }
    this.valueChange.emit(target.value);
  }
}
