import {Routes} from '@angular/router';
import {ProjectsPage} from './projects-page';
import {ProjectPage} from './project-page';

export const routes: Routes = [
  {path: '', redirectTo: 'projects', pathMatch: 'full'},
  {path: 'projects', component: ProjectsPage},
  {path: 'projects/new', component: ProjectPage},
  {path: 'projects/:id', component: ProjectPage},
  {path: '**', redirectTo: 'projects'},
];
