import {computed, inject, Injectable} from '@angular/core';
import {TUI_DARK_MODE} from '@taiga-ui/core';

/** Тема поверх TUI_DARK_MODE: выбор сохраняется, «как в системе» сбрасывает его. */
@Injectable({providedIn: 'root'})
export class ThemeService {
  private readonly mode = inject(TUI_DARK_MODE);

  readonly dark = computed(() => this.mode());

  toggle(): void {
    this.mode.set(!this.mode());
  }

  followSystem(): void {
    this.mode.reset();
  }
}
