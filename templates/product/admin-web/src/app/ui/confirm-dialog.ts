import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MAT_DIALOG_DATA, MatDialogModule} from '@angular/material/dialog';

export interface ConfirmDialogData {
  title: string;
  message: string;
  confirm?: string;
  cancel?: string;
}

@Component({
  selector: 'app-confirm-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatDialogModule, MatButtonModule],
  template: `
    <h2 mat-dialog-title>{{ data.title }}</h2>
    <mat-dialog-content>{{ data.message }}</mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button type="button" data-testid="confirm.cancel" [mat-dialog-close]="false">
        {{ data.cancel ?? 'Cancel' }}
      </button>
      <button mat-flat-button type="button" data-testid="confirm.ok" [mat-dialog-close]="true">
        {{ data.confirm ?? 'Confirm' }}
      </button>
    </mat-dialog-actions>
  `,
})
export class AppConfirmDialog {
  readonly data = inject<ConfirmDialogData>(MAT_DIALOG_DATA);
}
