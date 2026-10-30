import {Dialog} from '@angular/cdk/dialog';
import {inject, Injectable, Injector} from '@angular/core';
import {RunDialog, RunDialogData} from './run-dialog';

/** Открывает диалог запуска агента в контексте проекта: диалог видит WorkspaceStore через injector. */
@Injectable()
export class RunLauncher {
  private readonly dialog = inject(Dialog);
  private readonly injector = inject(Injector);

  open(stageKey: string | null = null, agent: string | null = null): void {
    this.dialog.open<unknown, RunDialogData>(RunDialog, {
      data: {stageKey, agent},
      injector: this.injector,
      backdropClass: 'dialog-backdrop',
      panelClass: 'dialog-panel',
      autoFocus: 'first-tabbable',
      restoreFocus: true,
      ariaLabelledBy: 'run-title',
    });
  }
}
