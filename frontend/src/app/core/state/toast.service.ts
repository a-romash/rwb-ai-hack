import {Injectable, signal} from '@angular/core';
import {Tone} from '../pipeline/status';

export interface ToastAction {
  label: string;
  run: () => void;
}

export interface Toast {
  id: number;
  tone: Tone;
  title: string;
  text?: string;
  action?: ToastAction;
}

/** Короткие уведомления о результате действия. Объявляются через aria-live в ToastHost. */
@Injectable({providedIn: 'root'})
export class ToastService {
  private next = 1;
  private readonly timers = new Map<number, ReturnType<typeof setTimeout>>();
  readonly items = signal<Toast[]>([]);

  show(toast: Omit<Toast, 'id'>, ttl = 5200): number {
    const id = this.next++;
    this.items.update(list => [...list.slice(-3), {...toast, id}]);
    this.timers.set(id, setTimeout(() => this.dismiss(id), ttl));
    return id;
  }

  success(title: string, text?: string, action?: ToastAction): number {
    return this.show({tone: 'ok', title, text, action});
  }

  error(title: string, text?: string, action?: ToastAction): number {
    return this.show({tone: 'fail', title, text, action}, 9000);
  }

  info(title: string, text?: string, action?: ToastAction): number {
    return this.show({tone: 'run', title, text, action});
  }

  dismiss(id: number): void {
    clearTimeout(this.timers.get(id));
    this.timers.delete(id);
    this.items.update(list => list.filter(item => item.id !== id));
  }

  /** Пока пользователь читает уведомление, оно не исчезает. */
  hold(id: number): void {
    clearTimeout(this.timers.get(id));
  }

  release(id: number): void {
    this.timers.set(id, setTimeout(() => this.dismiss(id), 2400));
  }
}
