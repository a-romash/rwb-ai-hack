import {DatePipe} from '@angular/common';
import {Component, DestroyRef, inject, signal} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {FormControl, FormGroup, ReactiveFormsModule, Validators} from '@angular/forms';
import {ActivatedRoute, Router, RouterLink} from '@angular/router';
import {TuiButton, TuiInput, TuiTextfield} from '@taiga-ui/core';
import {TuiTextarea} from '@taiga-ui/kit';
import {errorMessage, Project, ProjectsApi} from './api';

@Component({
  selector: 'app-project-page',
  imports: [DatePipe, RouterLink, ReactiveFormsModule, TuiButton, TuiInput, TuiTextfield, TuiTextarea],
  template: `
    <a class="back-link" routerLink="/projects">← Все проекты</a>
    <div class="page-heading">
      <div><div class="eyebrow">{{ isNew ? 'НОВЫЙ ПРОЕКТ' : 'КАРТОЧКА ПРОЕКТА' }}</div>
      <h1>{{ isNew ? 'Опишите вашу задачу' : (project()?.name || 'Проект') }}</h1>
      <p class="muted">{{ isNew ? 'Начните с цели и ожидаемого результата.' : 'Требования и последовательность этапов разработки.' }}</p></div>
      @if (project()) { <span class="badge">Не запущен</span> }
    </div>
    @if (loading()) {
      <div class="empty-state" role="status">Загружаем проект…</div>
    } @else if (!isNew && !project()) {
      <div class="error-panel" role="alert"><p>{{ error() }}</p><button tuiButton appearance="secondary" size="s" (click)="load()">Повторить</button></div>
    } @else {
      <div class="detail-grid">
        <section class="panel">
          <div class="panel-heading"><h2>Бизнес-требования</h2><span class="muted">01 / Входные данные</span></div>
          <form [formGroup]="form" (ngSubmit)="save()">
            <fieldset [disabled]="saving()">
              <label class="field-label" for="project-name">Название проекта</label>
              <tui-textfield><input tuiInput id="project-name" formControlName="name" maxlength="200" placeholder="Например, помощник водителя" /></tui-textfield>
              @if (form.controls.name.touched && form.controls.name.invalid) { <p class="field-error">Введите название: от 1 до 200 символов.</p> }
              <div class="label-row"><label class="field-label" for="project-requirements">Что нужно создать?</label><span class="muted">{{ form.controls.requirements.value.length }} / 50 000</span></div>
              <tui-textfield><textarea tuiTextarea id="project-requirements" formControlName="requirements" maxlength="50000" [min]="12" placeholder="Опишите проблему, пользователей и ожидаемый результат…"></textarea></tui-textfield>
              @if (form.controls.requirements.touched && form.controls.requirements.invalid) { <p class="field-error">Введите требования: от 1 до 50 000 символов.</p> }
              <p class="form-hint">Укажите бизнес-цель, основные сценарии и ограничения.</p>
            </fieldset>
            @if (error()) { <p class="field-error" role="alert">{{ error() }}</p> }
            <div class="form-actions"><button tuiButton type="submit" size="m" [disabled]="saving()">{{ saving() ? 'Сохраняем…' : (isNew ? 'Создать проект' : 'Сохранить изменения') }}</button><span class="save-status" role="status">{{ saved() ? 'Изменения сохранены' : '' }}</span></div>
          </form>
          @if (project(); as p) { <p class="metadata">Последнее изменение: {{ p.updated_at | date:'d MMMM y, HH:mm' }}</p> }
        </section>
        <section class="panel pipeline-panel">
          <div class="panel-heading"><h2>Пайплайн</h2><span class="count">{{ project()?.stages?.length || 10 }}</span></div>
          @if (project(); as p) {
            <ol class="stages">
              @for (stage of p.stages; track stage.id) {
                <li><span class="stage-number">{{ stage.position.toString().padStart(2, '0') }}</span><div><span class="stage-name">{{ stage.name }}</span><span class="stage-status">Не запущен</span></div><span class="stage-dot" aria-hidden="true"></span></li>
              }
            </ol>
          } @else {
            <div class="pipeline-placeholder"><span aria-hidden="true">↗</span><h3>От требований до продукта</h3><p>После создания проекта здесь появятся 10 этапов разработки.</p></div>
          }
          <p class="pipeline-note">Исполнение этапов пока не подключено.</p>
        </section>
      </div>
    }
  `,
})
export class ProjectPage {
  private readonly api = inject(ProjectsApi);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  readonly id = inject(ActivatedRoute).snapshot.paramMap.get('id');
  readonly isNew = !this.id;
  readonly project = signal<Project | null>(null);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly saved = signal(false);
  readonly error = signal('');
  readonly form = new FormGroup({
    name: new FormControl('', {nonNullable: true, validators: [Validators.required, Validators.maxLength(200), Validators.pattern(/\S/)]}),
    requirements: new FormControl('', {nonNullable: true, validators: [Validators.required, Validators.maxLength(50000), Validators.pattern(/\S/)]}),
  });

  constructor() {
    if (this.id) this.load();
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.saved.set(false));
  }

  load() {
    if (!this.id) return;
    this.loading.set(true);
    this.error.set('');
    this.api.get(this.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: project => { this.project.set(project); this.form.reset(project); this.loading.set(false); },
      error: error => { this.error.set(errorMessage(error)); this.loading.set(false); },
    });
  }

  save() {
    if (this.saving()) return;
    this.form.markAllAsTouched();
    if (this.form.invalid) return;
    this.saving.set(true);
    this.error.set('');
    this.saved.set(false);
    const raw = this.form.getRawValue();
    const data = {name: raw.name.trim(), requirements: raw.requirements.trim()};
    const request = this.id ? this.api.update(this.id, data) : this.api.create(data);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: project => {
        this.saving.set(false);
        if (this.isNew) { void this.router.navigate(['/projects', project.id]); return; }
        this.project.set(project);
        this.form.reset(project);
        this.saved.set(true);
      },
      error: error => { this.error.set(errorMessage(error)); this.saving.set(false); },
    });
  }
}
