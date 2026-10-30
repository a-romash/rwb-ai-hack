import {Dialog, DIALOG_DATA, DialogRef} from '@angular/cdk/dialog';
import {ChangeDetectionStrategy, Component, inject, Injectable} from '@angular/core';
import {TuiButton} from '@taiga-ui/core';
import {Observable, map} from 'rxjs';

export interface ConfirmOptions {
  title: string;
  text: string;
  confirm: string;
  cancel: string;
  danger?: boolean;
}

@Component({
  selector: 'app-confirm-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiButton],
  host: {class: 'dialog-surface', role: 'alertdialog', 'aria-modal': 'true', 'aria-labelledby': 'confirm-title', 'aria-describedby': 'confirm-text'},
  template: `
    <h2 id="confirm-title" class="title">{{ data.title }}</h2>
    <p id="confirm-text" class="text">{{ data.text }}</p>
    <div class="actions">
      <button tuiButton type="button" appearance="secondary" size="s" (click)="ref.close(false)" cdkFocusInitial>{{ data.cancel }}</button>
      <button tuiButton type="button" size="s" [appearance]="data.danger ? 'accent' : 'primary'" [class.danger]="data.danger" (click)="ref.close(true)">
        {{ data.confirm }}
      </button>
    </div>
  `,
  styles: `
    :host { display: block; width: min(420px, calc(100vw - 32px)); padding: 20px 24px 16px; }
    .title { font-size: var(--p-text-l); line-height: 1.5rem; letter-spacing: -0.011em; }
    .text { margin-top: 6px; color: var(--p-ink-2); line-height: 1.25rem; }
    .actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; margin-top: 20px; }
    .danger { --tui-background-accent-2: var(--p-fail); --tui-background-accent-2-hover: var(--p-fail-text); --tui-background-accent-2-pressed: var(--p-fail-text); }
  `,
})
export class ConfirmDialog {
  protected readonly data = inject<ConfirmOptions>(DIALOG_DATA);
  protected readonly ref = inject<DialogRef<boolean>>(DialogRef);
}

/** Подтверждение необратимого или неочевидного действия. */
@Injectable({providedIn: 'root'})
export class Confirm {
  private readonly dialog = inject(Dialog);

  ask(options: ConfirmOptions): Observable<boolean> {
    const ref = this.dialog.open<boolean, ConfirmOptions>(ConfirmDialog, {
      data: options,
      backdropClass: 'dialog-backdrop',
      panelClass: 'dialog-panel',
      autoFocus: 'first-tabbable',
      restoreFocus: true,
    });
    return ref.closed.pipe(map(result => result === true));
  }
}
