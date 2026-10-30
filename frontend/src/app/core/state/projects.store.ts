import {computed, inject, Injectable, signal} from '@angular/core';
import {Project, ProjectSummary} from '../api/api.types';
import {readableError, ReadableError} from '../api/errors';
import {StudioApi} from '../api/projects.api';

type LoadState = 'idle' | 'loading' | 'ready' | 'error';

/** Список проектов. Общий для страницы проектов и командной палитры. */
@Injectable({providedIn: 'root'})
export class ProjectsStore {
  private readonly api = inject(StudioApi);

  readonly items = signal<ProjectSummary[]>([]);
  readonly state = signal<LoadState>('idle');
  readonly error = signal<ReadableError | null>(null);
  readonly loading = computed(() => this.state() === 'loading');

  load(): void {
    this.state.set('loading');
    this.error.set(null);
    this.api.listProjects().subscribe({
      next: items => {
        this.items.set(items);
        this.state.set('ready');
      },
      error: error => {
        this.error.set(readableError(error, 'projects'));
        this.state.set('error');
      },
    });
  }

  /** Первичная загрузка без повторов, если список уже есть. */
  ensure(): void {
    if (this.state() === 'idle' || this.state() === 'error') this.load();
  }

  /** Обновляет запись после создания или сохранения проекта, не перезапрашивая список. */
  upsert(project: Project | ProjectSummary): void {
    const summary: ProjectSummary = {
      id: project.id,
      name: project.name,
      created_at: project.created_at,
      updated_at: project.updated_at,
    };
    this.items.update(list => {
      const rest = list.filter(item => item.id !== summary.id);
      return [summary, ...rest].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
    });
  }
}
