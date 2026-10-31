import {DestroyRef, Injectable, effect, inject, signal} from '@angular/core';
import {apiUrl, connectSse, readSseEvents} from '../api/sse';
import {MODEL} from '../generated/model';
import {Session} from './session';

/** A domain event from the product outbox (GET /api/events/stream). */
export interface LiveEvent {
  id: number;
  type: string;
  entity: string;
  entity_id: string;
  payload: Record<string, unknown>;
  occurred_at: string;
}

export interface AppNotification {
  id: number;
  name: string;
  text: string;
  channels: string[];
  created_at: string;
}

/**
 * One SSE stream per app for the signed-in role. Screens subscribe to the event types of their
 * `live` list; every event also pulls new notifications of the role, shown as a browser
 * notification when the device allows it. The stream reconnects with a growing pause and resumes
 * after the last seen event.
 */
@Injectable({providedIn: 'root'})
export class LiveEvents {
  readonly connected = signal(false);
  readonly notifications = signal<AppNotification[]>([]);
  private readonly session = inject(Session);
  private readonly listeners = new Set<(event: LiveEvent) => void>();
  private abort: AbortController | null = null;
  private lastEvent = 0;
  private lastNotification = 0;

  constructor() {
    effect(() => {
      const role = this.session.role();
      this.stop();
      this.notifications.set([]);
      this.lastNotification = 0;
      if (role) {
        void this.run();
      }
    });
    inject(DestroyRef).onDestroy(() => this.stop());
  }

  /** Calls the handler for events of the given types; returns the unsubscribe function. */
  on(types: string[], handler: (event: LiveEvent) => void): () => void {
    const wanted = new Set(types);
    const listener = (event: LiveEvent) => wanted.has(event.type) && handler(event);
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private stop(): void {
    this.abort?.abort();
    this.abort = null;
    this.connected.set(false);
  }

  private async run(): Promise<void> {
    const abort = (this.abort = new AbortController());
    await this.pullNotifications(true);
    for (let pause = 1000; !abort.signal.aborted; pause = Math.min(pause * 2, 30_000)) {
      try {
        const stream = await connectSse(apiUrl(`/events/stream?after=${this.lastEvent}`), {
          authorization: await this.session.authorization(),
          signal: abort.signal,
        });
        this.connected.set(true);
        pause = 1000;
        for await (const data of readSseEvents(stream)) {
          const event = JSON.parse(data) as LiveEvent;
          this.lastEvent = Math.max(this.lastEvent, event.id);
          this.listeners.forEach((listener) => listener(event));
          await this.pullNotifications(false);
        }
      } catch {
        // Network or auth error: wait and reconnect unless the role changed.
      }
      this.connected.set(false);
      if (!abort.signal.aborted) {
        await new Promise((resolve) => setTimeout(resolve, pause));
      }
    }
  }

  private async pullNotifications(first: boolean): Promise<void> {
    try {
      const fresh = await this.session.request<AppNotification[]>('GET', `/notifications?after=${this.lastNotification}`);
      if (!fresh.length) return;
      this.lastNotification = fresh[fresh.length - 1].id;
      this.notifications.update((list) => [...fresh.reverse(), ...list].slice(0, 50));
      if (!first) {
        fresh.forEach((item) => show(item));
      }
    } catch {
      // Notifications are optional; the event stream keeps working.
    }
  }
}

function show(item: AppNotification): void {
  if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return;
  if (!MODEL.device.includes('local_notification') && !item.channels.includes('web')) return;
  new Notification(MODEL.title || 'Уведомление', {body: item.text, tag: `notification-${item.id}`});
}
