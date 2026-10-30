import {HttpClient} from '@angular/common/http';
import {inject, Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {Health, JobCreate, JobRead, Project, ProjectInput, ProjectPatch, ProjectSummary} from './api.types';

/** HTTP-клиент API Студии. Пути совпадают с роутерами FastAPI (`/api/projects`, `/api/health`). */
@Injectable({providedIn: 'root'})
export class StudioApi {
  private readonly http = inject(HttpClient);

  listProjects(): Observable<ProjectSummary[]> {
    return this.http.get<ProjectSummary[]>('/api/projects');
  }

  getProject(id: string): Observable<Project> {
    return this.http.get<Project>(`/api/projects/${encodeURIComponent(id)}`);
  }

  createProject(data: ProjectInput): Observable<Project> {
    return this.http.post<Project>('/api/projects', data);
  }

  updateProject(id: string, data: ProjectPatch): Observable<Project> {
    return this.http.patch<Project>(`/api/projects/${encodeURIComponent(id)}`, data);
  }

  createJob(projectId: string, data: JobCreate): Observable<JobRead> {
    return this.http.post<JobRead>(`/api/projects/${encodeURIComponent(projectId)}/jobs`, data);
  }

  getJob(projectId: string, jobId: string): Observable<JobRead> {
    return this.http.get<JobRead>(`/api/projects/${encodeURIComponent(projectId)}/jobs/${encodeURIComponent(jobId)}`);
  }

  health(): Observable<Health> {
    return this.http.get<Health>('/api/health');
  }
}
