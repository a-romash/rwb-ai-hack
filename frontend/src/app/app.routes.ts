import {Routes} from '@angular/router';
import {unsavedChangesGuard} from './core/state/unsaved-changes.guard';

export const routes: Routes = [
  {path: '', pathMatch: 'full', redirectTo: 'projects'},
  {
    path: 'projects',
    title: 'Проекты — Поток',
    loadComponent: () => import('./features/projects/projects-page').then(m => m.ProjectsPage),
  },
  {
    path: 'projects/new',
    title: 'Новый проект — Поток',
    loadComponent: () => import('./features/composer/composer-page').then(m => m.ComposerPage),
    canDeactivate: [unsavedChangesGuard],
  },
  {
    path: 'projects/:id',
    loadComponent: () => import('./features/workspace/workspace-page').then(m => m.WorkspacePage),
    children: [
      {path: '', pathMatch: 'full', redirectTo: 'flow'},
      {
        path: 'flow',
        loadComponent: () => import('./features/workspace/flow-tab').then(m => m.FlowTab),
      },
      {
        path: 'requirements',
        loadComponent: () => import('./features/workspace/requirements-tab').then(m => m.RequirementsTab),
        canDeactivate: [unsavedChangesGuard],
      },
      {
        path: 'runs',
        loadComponent: () => import('./features/workspace/runs-tab').then(m => m.RunsTab),
      },
    ],
  },
  {
    path: '**',
    title: 'Страница не найдена — Поток',
    loadComponent: () => import('./features/not-found/not-found-page').then(m => m.NotFoundPage),
  },
];
