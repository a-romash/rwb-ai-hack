import {DatePipe} from '@angular/common';
import {Component, DestroyRef, inject, signal} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {RouterLink} from '@angular/router';
import {TuiButton} from '@taiga-ui/core';
import {errorMessage, ProjectsApi, ProjectSummary} from './api';

@Component({
  selector: 'app-projects-page',
  imports: [RouterLink, DatePipe, TuiButton],
  template: `
    <div class="eyebrow">РАБОЧЕЕ ПРОСТРАНСТВО</div>
    <div class="page-heading">
      <div><h1>Проекты</h1><p class="muted">Бизнес-требования и этапы разработки в одном месте.</p></div>
      <a tuiButton size="m" routerLink="/projects/new">+ Создать проект</a>
    </div>
    <div class="section-line"><h2>Все проекты <span class="count">{{ projects().length }}</span></h2><span class="muted">Сначала новые</span></div>
    @if (loading()) {
      <div class="empty-state" role="status">Загружаем проекты…</div>
    } @else if (error()) {
      <div class="error-panel" role="alert"><p>{{ error() }}</p><button tuiButton appearance="secondary" size="s" (click)="load()">Повторить</button></div>
    } @else if (!projects().length) {
      <section class="empty-state">
        <span class="empty-icon" aria-hidden="true">↗</span>
        <h2>Начните с бизнес-задачи</h2>
        <p>Опишите, какой продукт нужен.<br>В карточке проекта появится последовательность этапов разработки.</p>
        <a tuiButton appearance="secondary" size="m" routerLink="/projects/new">Создать первый проект</a>
      </section>
    } @else {
      <div class="project-grid">
        @for (project of projects(); track project.id) {
          <a class="project-card" [routerLink]="['/projects', project.id]">
            <div class="card-top"><span class="project-icon" aria-hidden="true">▦</span><span class="badge">Не запущен</span></div>
            <h2>{{ project.name }}</h2>
            <p class="muted">10 этапов разработки</p>
            <div class="card-footer"><span>Изменён {{ project.updated_at | date:'d MMM y, HH:mm' }}</span><span aria-hidden="true">↗</span></div>
          </a>
        }
      </div>
    }
    <p class="footnote">Исполнение этапов будет доступно после подключения ИИ-агентов.</p>
  `,
})
export class ProjectsPage {
  private readonly api = inject(ProjectsApi);
  private readonly destroyRef = inject(DestroyRef);
  readonly projects = signal<ProjectSummary[]>([]);
  readonly loading = signal(false);
  readonly error = signal('');

  constructor() { this.load(); }

  load() {
    this.loading.set(true);
    this.error.set('');
    this.api.list().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: projects => { this.projects.set(projects); this.loading.set(false); },
      error: error => { this.error.set(errorMessage(error)); this.loading.set(false); },
    });
  }
}
