import {ChangeDetectionStrategy, Component, computed, inject, signal, viewChild} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {ActivatedRoute, Router, RouterLink} from '@angular/router';
import {TuiButton, TuiIcon, TuiInput} from '@taiga-ui/core';
import {readableError, ReadableError} from '../../core/api/errors';
import {StudioApi} from '../../core/api/projects.api';
import {ProjectsStore} from '../../core/state/projects.store';
import {ShellService} from '../../core/state/shell.service';
import {ToastService} from '../../core/state/toast.service';
import {HasUnsavedChanges} from '../../core/state/unsaved-changes.guard';
import {PARKING_EXAMPLE, REQUIREMENTS_TEMPLATE} from '../../core/util/examples';
import {RequirementsEditor} from '../../shared/ui/requirements-editor/requirements-editor';
import {RequirementsInsights} from '../../shared/ui/requirements-insights';

const NAME_MAX = 200;
const REQUIREMENTS_MAX = 50_000;

@Component({
  selector: 'app-composer-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, TuiButton, TuiIcon, TuiInput, RequirementsEditor, RequirementsInsights],
  templateUrl: './composer-page.html',
  styleUrl: './composer-page.less',
  host: {'(document:keydown)': 'onKeydown($event)'},
})
export class ComposerPage implements HasUnsavedChanges {
  private readonly api = inject(StudioApi);
  private readonly router = inject(Router);
  private readonly projects = inject(ProjectsStore);
  private readonly toasts = inject(ToastService);
  private readonly editor = viewChild(RequirementsEditor);

  protected readonly name = signal('');
  protected readonly requirements = signal('');
  protected readonly submitted = signal(false);
  protected readonly saving = signal(false);
  protected readonly error = signal<ReadableError | null>(null);
  private created = false;

  protected readonly isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
  protected readonly nameError = computed(() => {
    const value = this.name().trim();
    if (!value) return 'Назовите проект: так его будет проще найти.';
    if (value.length > NAME_MAX) return `Название длиннее ${NAME_MAX} символов. Сократите его.`;
    return null;
  });
  protected readonly requirementsError = computed(() => {
    const value = this.requirements().trim();
    if (!value) return 'Опишите, что нужно создать. Без требований агентам не с чем работать.';
    if (value.length > REQUIREMENTS_MAX) return 'Требования длиннее 50 000 символов. Сократите текст.';
    return null;
  });
  protected readonly valid = computed(() => !this.nameError() && !this.requirementsError());

  constructor() {
    const shell = inject(ShellService);
    shell.crumbs.set([{label: 'Проекты', link: '/projects'}, {label: 'Новый проект'}]);
    shell.projectId.set(null);
    if (inject(ActivatedRoute).snapshot.queryParamMap.get('example') === 'parking') this.useExample();
  }

  hasUnsavedChanges(): boolean {
    return !this.created && Boolean(this.name().trim() || this.requirements().trim());
  }

  protected useExample(): void {
    if (!this.name().trim()) this.name.set(PARKING_EXAMPLE.name);
    this.requirements.set(PARKING_EXAMPLE.requirements);
  }

  protected useTemplate(): void {
    const current = this.requirements().trimEnd();
    this.requirements.set(current ? `${current}\n\n${REQUIREMENTS_TEMPLATE}` : REQUIREMENTS_TEMPLATE);
    this.editor()?.focus();
  }

  protected onFileError(message: string): void {
    this.toasts.error('Файл не загружен', message);
  }

  protected create(): void {
    this.submitted.set(true);
    if (!this.valid() || this.saving()) {
      if (this.nameError()) document.getElementById('project-name')?.focus();
      else this.editor()?.focus();
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    this.api.createProject({name: this.name().trim(), requirements: this.requirements().trim()}).subscribe({
      next: project => {
        this.created = true;
        this.projects.upsert(project);
        this.toasts.success('Проект создан', 'Начните с бизнес-анализа: он найдёт пробелы в требованиях.');
        void this.router.navigate(['/projects', project.id, 'flow']);
      },
      error: error => {
        this.saving.set(false);
        this.error.set(readableError(error, 'save'));
      },
    });
  }

  protected onKeydown(event: KeyboardEvent): void {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      this.create();
    }
  }
}
