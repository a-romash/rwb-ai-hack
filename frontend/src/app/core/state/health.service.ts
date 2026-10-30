import {DestroyRef, inject, Injectable, signal} from '@angular/core';
import {StudioApi} from '../api/projects.api';

export type HealthState = 'unknown' | 'ok' | 'down';

/** Опрос /api/health: раз в 20 секунд, на скрытой вкладке — пауза. */
@Injectable({providedIn: 'root'})
export class HealthService {
  private readonly api = inject(StudioApi);
  readonly state = signal<HealthState>('unknown');
  readonly checkedAt = signal<number | null>(null);
  private timer: ReturnType<typeof setTimeout> | null = null;
  private inFlight = false;

  constructor() {
    const onVisibility = () => {
      if (document.visibilityState === 'visible') this.check();
    };
    document.addEventListener('visibilitychange', onVisibility);
    inject(DestroyRef).onDestroy(() => {
      document.removeEventListener('visibilitychange', onVisibility);
      if (this.timer) clearTimeout(this.timer);
    });
    this.check();
  }

  check(): void {
    if (this.inFlight) return;
    this.inFlight = true;
    if (this.timer) clearTimeout(this.timer);
    this.api.health().subscribe({
      next: () => this.settle('ok'),
      error: () => this.settle('down'),
    });
  }

  private settle(state: HealthState): void {
    this.inFlight = false;
    this.state.set(state);
    this.checkedAt.set(Date.now());
    if (document.visibilityState === 'visible') {
      this.timer = setTimeout(() => this.check(), state === 'ok' ? 20_000 : 6_000);
    }
  }
}
