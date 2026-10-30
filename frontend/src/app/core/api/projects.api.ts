import {HttpClient} from '@angular/common/http';
import {inject, Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {
  ArtifactRead,
  AttachmentRead,
  Health,
  JobCreate,
  JobRead,
  Project,
  ProjectInput,
  ProjectPatch,
  ProjectSummary,
  RunCreate,
  RunRead,
  RunSummary,
} from './api.types';

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

  createRun(projectId: string, data: RunCreate): Observable<RunRead> {
    return this.http.post<RunRead>(`/api/projects/${encodeURIComponent(projectId)}/runs`, data);
  }

  listRuns(projectId: string): Observable<RunSummary[]> {
    return this.http.get<RunSummary[]>(`/api/projects/${encodeURIComponent(projectId)}/runs`);
  }

  getRun(runId: string): Observable<RunRead> {
    return this.http.get<RunRead>(`/api/runs/${encodeURIComponent(runId)}`);
  }

  artifacts(runId: string): Observable<ArtifactRead[]> {
    return this.http.get<ArtifactRead[]>(`/api/runs/${encodeURIComponent(runId)}/artifacts`);
  }

  attachments(projectId: string): Observable<AttachmentRead[]> {
    return this.http.get<AttachmentRead[]>(`/api/projects/${encodeURIComponent(projectId)}/attachments`);
  }

  /** Тело запроса — сам файл; имя идёт параметром, бэкенд проверяет его и формат. */
  uploadAttachment(projectId: string, file: File): Observable<AttachmentRead> {
    return this.http.post<AttachmentRead>(`/api/projects/${encodeURIComponent(projectId)}/attachments`, file, {
      params: {name: file.name},
      headers: {'Content-Type': 'application/octet-stream'},
    });
  }

  /** Файл рабочей области прогона: ссылка открывается в новой вкладке. */
  fileUrl(runId: string, path: string): string {
    return `/api/runs/${encodeURIComponent(runId)}/files?path=${encodeURIComponent(path)}`;
  }

  retryStage(runId: string, key: string): Observable<unknown> {
    return this.http.post(`/api/runs/${encodeURIComponent(runId)}/stages/${encodeURIComponent(key)}/retry`, {});
  }

  answer(runId: string, answers: Record<string, string>): Observable<unknown> {
    return this.http.post(`/api/runs/${encodeURIComponent(runId)}/answers`, {answers});
  }

  decide(runId: string, gate: string, decision: 'approve' | 'reject', comment = ''): Observable<unknown> {
    return this.http.post(`/api/runs/${encodeURIComponent(runId)}/gates/${encodeURIComponent(gate)}/decision`, {decision, comment});
  }

  cancelRun(runId: string): Observable<unknown> {
    return this.http.post(`/api/runs/${encodeURIComponent(runId)}/cancel`, {});
  }

  /** SSE прогона; EventSource сам переподключается и передаёт Last-Event-ID. */
  runEvents(runId: string): EventSource {
    return new EventSource(`/api/runs/${encodeURIComponent(runId)}/events/stream`);
  }

  health(): Observable<Health> {
    return this.http.get<Health>('/api/health');
  }
}
