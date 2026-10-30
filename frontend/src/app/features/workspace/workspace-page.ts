import {ChangeDetectionStrategy, Component, computed, DestroyRef, effect, ElementRef, inject, signal, viewChild} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {FormsModule} from '@angular/forms';
import {Title} from '@angular/platform-browser';
import {ActivatedRoute, RouterLink, RouterLinkActive, RouterOutlet} from '@angular/router';
import {TuiButton, TuiHint, TuiIcon, TuiInput} from '@taiga-ui/core';
import {TuiSkeleton} from '@taiga-ui/kit';
import {readableError} from '../../core/api/errors';
import {AGENTS} from '../../core/pipeline/agents.catalog';
import {Clock} from '../../core/state/clock.service';
import {ShellService} from '../../core/state/shell.service';
import {ToastService} from '../../core/state/toast.service';
import {plural} from '../../core/util/text';
import {fullDate} from '../../core/util/time';
import {PipelineMini} from '../../shared/ui/pipeline/pipeline-mini';
import {RelTimePipe} from '../../shared/ui/rel-time.pipe';
import {RunLauncher} from './run-launcher';
import {WorkspaceStore} from './workspace.store';

@Component({
  selector: 'app-workspace-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, FormsModule, TuiButton, TuiHint, TuiIcon, TuiInput, TuiSkeleton, PipelineMini, RelTimePipe],
  providers: [WorkspaceStore, RunLauncher],
  templateUrl: './workspace-page.html',
  styleUrl: './workspace-page.less',
})
export class WorkspacePage {
  protected readonly store = inject(WorkspaceStore);
  protected readonly clock = inject(Clock);
  private readonly launcher = inject(RunLauncher);
  private readonly toasts = inject(ToastService);
  private readonly renameInput = viewChild<ElementRef<HTMLInputElement>>('renameInput');

  protected readonly renaming = signal(false);
  protected readonly draftName = signal('');
  protected readonly savingName = signal(false);
  protected readonly fullDate = fullDate;
  protected readonly analyst = AGENTS.analyst;

  protected readonly done = computed(() => this.store.stages().filter(stage => stage.tone === 'ok').length);
  protected readonly stagesLabel = computed(() => {
    const total = this.store.stages().length;
    return `${this.done()} из ${total} ${plural(total, ['шага', 'шагов', 'шагов'])} конвейера готово`;
  });

  constructor() {
    const shell = inject(ShellService);
    const title = inject(Title);
    inject(ActivatedRoute)
      .paramMap.pipe(takeUntilDestroyed())
      .subscribe(params => {
        const id = params.get('id');
        if (id) this.store.open(id);
      });

    effect(() => {
      const project = this.store.project();
      shell.projectId.set(this.store.id());
      shell.crumbs.set([{label: 'Проекты', link: '/projects'}, {label: project?.name ?? 'Проект'}]);
      if (project) title.setTitle(`${project.name} — Поток`);
    });

    inject(DestroyRef).onDestroy(() => shell.projectId.set(null));
  }

  protected runAnalyst(): void {
    this.launcher.open('analysis', 'analyst');
  }

  protected startRename(): void {
    this.draftName.set(this.store.project()?.name ?? '');
    this.renaming.set(true);
    queueMicrotask(() => {
      const input = this.renameInput()?.nativeElement;
      input?.focus();
      input?.select();
    });
  }

  protected cancelRename(): void {
    this.renaming.set(false);
  }

  protected saveRename(): void {
    const name = this.draftName().trim();
    const current = this.store.project()?.name;
    if (!name || name.length > 200) {
      this.toasts.error('Название не сохранено', 'Название должно быть от 1 до 200 символов.');
      return;
    }
    if (name === current) {
      this.renaming.set(false);
      return;
    }
    this.savingName.set(true);
    this.store.save({name}).subscribe({
      next: () => {
        this.savingName.set(false);
        this.renaming.set(false);
        this.toasts.success('Проект переименован');
      },
      error: error => {
        this.savingName.set(false);
        const readable = readableError(error, 'save');
        this.toasts.error('Название не сохранено', readable.hint);
      },
    });
  }

  protected onRenameKey(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      event.preventDefault();
      this.saveRename();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      this.cancelRename();
    }
  }
}
