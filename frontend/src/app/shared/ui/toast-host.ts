import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {TuiButton, TuiIcon} from '@taiga-ui/core';
import {Toast, ToastService} from '../../core/state/toast.service';

const ICONS: Record<string, string> = {
  ok: '@tui.circle-check',
  fail: '@tui.circle-x',
  run: '@tui.info',
  wait: '@tui.triangle-alert',
  idle: '@tui.info',
};

/** Стопка уведомлений в правом нижнем углу. Новые объявляются скринридером. */
@Component({
  selector: 'app-toast-host',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiButton, TuiIcon],
  template: `
    <section class="stack" aria-label="Уведомления" aria-live="polite" aria-relevant="additions">
      @for (toast of toasts.items(); track toast.id) {
        <div class="toast" [attr.data-tone]="toast.tone" (mouseenter)="toasts.hold(toast.id)" (mouseleave)="toasts.release(toast.id)" (focusin)="toasts.hold(toast.id)">
          <tui-icon class="icon" [icon]="icon(toast)" />
          <div class="body">
            <p class="title">{{ toast.title }}</p>
            @if (toast.text) {
              <p class="text">{{ toast.text }}</p>
            }
            @if (toast.action; as action) {
              <button tuiButton type="button" size="xs" appearance="secondary" class="action" (click)="run(toast)">{{ action.label }}</button>
            }
          </div>
          <button tuiIconButton type="button" size="xs" appearance="flat" iconStart="@tui.x" class="close" (click)="toasts.dismiss(toast.id)">
            Закрыть уведомление
          </button>
        </div>
      }
    </section>
  `,
  styles: `
    .stack {
      position: fixed;
      right: 16px;
      bottom: 16px;
      z-index: 1000;
      display: grid;
      gap: 8px;
      width: min(360px, calc(100vw - 32px));
      pointer-events: none;
    }
    .toast {
      display: grid;
      grid-template-columns: 16px 1fr auto;
      gap: 10px;
      align-items: start;
      padding: 12px 8px 12px 14px;
      border: 1px solid var(--p-border);
      border-radius: var(--p-radius-card);
      background: var(--p-surface);
      box-shadow: var(--p-shadow-pop);
      pointer-events: auto;
      animation: toast-in var(--p-base) var(--p-ease) both;
    }
    .icon { width: 16px; height: 16px; margin-top: 2px; color: var(--p-run); }
    [data-tone='ok'] .icon { color: var(--p-ok); }
    [data-tone='fail'] .icon { color: var(--p-fail); }
    [data-tone='wait'] .icon { color: var(--p-wait); }
    .body { display: grid; gap: 2px; min-width: 0; }
    .title { font-weight: 500; }
    .text { color: var(--p-ink-2); font-size: var(--p-text-s); line-height: 1.125rem; }
    .action { justify-self: start; margin-top: 6px; margin-left: -8px; }
    .close { margin-top: -4px; }
    @keyframes toast-in { from { opacity: 0; transform: translateY(6px); } }
  `,
})
export class ToastHost {
  protected readonly toasts = inject(ToastService);

  protected icon(toast: Toast): string {
    return ICONS[toast.tone] ?? ICONS['idle'];
  }

  protected run(toast: Toast): void {
    toast.action?.run();
    this.toasts.dismiss(toast.id);
  }
}
