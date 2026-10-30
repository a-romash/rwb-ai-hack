import {DestroyRef, inject, Injectable, signal} from '@angular/core';

/** Общие часы: относительное время и таймеры запусков обновляются раз в секунду из одного источника. */
@Injectable({providedIn: 'root'})
export class Clock {
  readonly now = signal(Date.now());

  constructor() {
    const id = setInterval(() => this.now.set(Date.now()), 1000);
    inject(DestroyRef).onDestroy(() => clearInterval(id));
  }
}
