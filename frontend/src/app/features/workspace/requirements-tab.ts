import {ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal, untracked, viewChild} from '@angular/core';
import {TuiButton, TuiIcon} from '@taiga-ui/core';
import {readableError} from '../../core/api/errors';
import {Clock} from '../../core/state/clock.service';
import {ToastService} from '../../core/state/toast.service';
import {HasUnsavedChanges} from '../../core/state/unsaved-changes.guard';
import {PARKING_EXAMPLE, REQUIREMENTS_TEMPLATE} from '../../core/util/examples';
import {RelTimePipe} from '../../shared/ui/rel-time.pipe';
import {RequirementsEditor} from '../../shared/ui/requirements-editor/requirements-editor';
import {RequirementsInsights} from '../../shared/ui/requirements-insights';
import {WorkspaceStore} from './workspace.store';

/** Вкладка «Требования»: документ проекта, подсказки по полноте и явное сохранение. */
@Component({
  selector: 'app-requirements-tab',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiButton, TuiIcon, RequirementsEditor, RequirementsInsights, RelTimePipe],
  templateUrl: './requirements-tab.html',
  styleUrl: './requirements-tab.less',
  host: {'(document:keydown)': 'onKeydown($event)'},
})
export class RequirementsTab implements HasUnsavedChanges {
  protected readonly store = inject(WorkspaceStore);
  protected readonly clock = inject(Clock);
  private readonly toasts = inject(ToastService);
  private readonly editor = viewChild(RequirementsEditor);

  protected readonly draft = signal('');
  protected readonly saving = signal(false);
  protected readonly saved = computed(() => this.store.project()?.requirements ?? '');
  protected readonly dirty = computed(() => this.draft() !== this.saved());
  protected readonly empty = computed(() => !this.draft().trim());
  protected readonly isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);

  constructor() {
    // Черновик следует за сохранённой версией, пока пользователь не начал править
    let syncedFrom: string | null = null;
    effect(() => {
      const saved = this.saved();
      untracked(() => {
        if (syncedFrom === null || this.draft() === syncedFrom) this.draft.set(saved);
        syncedFrom = saved;
      });
    });

    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (this.dirty()) event.preventDefault();
    };
    window.addEventListener('beforeunload', beforeUnload);
    inject(DestroyRef).onDestroy(() => window.removeEventListener('beforeunload', beforeUnload));
  }

  hasUnsavedChanges(): boolean {
    return this.dirty();
  }

  protected save(): void {
    if (!this.dirty() || this.saving()) return;
    const requirements = this.draft().trim();
    if (!requirements) {
      this.toasts.error('Требования не сохранены', 'Пустые требования сохранить нельзя: агентам не с чем будет работать.');
      return;
    }
    if (requirements.length > 50_000) {
      this.toasts.error('Требования не сохранены', 'Текст длиннее 50 000 символов. Сократите его.');
      return;
    }
    this.saving.set(true);
    this.store.save({requirements}).subscribe({
      next: () => {
        this.saving.set(false);
        this.draft.set(this.saved());
        this.toasts.success('Требования сохранены', 'Следующие запуски агентов получат новую версию.');
      },
      error: error => {
        this.saving.set(false);
        const readable = readableError(error, 'save');
        this.toasts.error(readable.title, readable.hint);
      },
    });
  }

  protected discard(): void {
    this.draft.set(this.saved());
  }

  protected useTemplate(): void {
    const current = this.draft().trimEnd();
    this.draft.set(current ? `${current}\n\n${REQUIREMENTS_TEMPLATE}` : REQUIREMENTS_TEMPLATE);
    this.editor()?.focus();
  }

  protected useExample(): void {
    this.draft.set(PARKING_EXAMPLE.requirements);
  }

  protected onFileError(message: string): void {
    this.toasts.error('Файл не загружен', message);
  }

  protected onKeydown(event: KeyboardEvent): void {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
      event.preventDefault();
      this.save();
    }
  }
}
