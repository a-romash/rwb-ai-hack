import {inject} from '@angular/core';
import {CanDeactivateFn} from '@angular/router';
import {Observable, of} from 'rxjs';
import {Confirm} from '../../shared/ui/confirm-dialog';

/** Экран с несохранёнными изменениями. */
export interface HasUnsavedChanges {
  hasUnsavedChanges(): boolean;
}

export const unsavedChangesGuard: CanDeactivateFn<HasUnsavedChanges> = (component): Observable<boolean> => {
  if (!component?.hasUnsavedChanges?.()) return of(true);
  return inject(Confirm).ask({
    title: 'Уйти без сохранения?',
    text: 'Изменения в требованиях пропадут. Чтобы их сохранить, останьтесь и нажмите «Сохранить».',
    confirm: 'Уйти без сохранения',
    cancel: 'Остаться',
    danger: true,
  });
};
