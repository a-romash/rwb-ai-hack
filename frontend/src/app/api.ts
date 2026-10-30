import {HttpClient, HttpErrorResponse} from '@angular/common/http';
import {inject, Injectable} from '@angular/core';

export interface ProjectSummary {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface Stage {
  id: string;
  key: string;
  name: string;
  position: number;
  status: 'not_started';
}

export interface Project extends ProjectSummary {
  requirements: string;
  stages: Stage[];
}

export interface ProjectInput {
  name: string;
  requirements: string;
}

@Injectable({providedIn: 'root'})
export class ProjectsApi {
  private readonly http = inject(HttpClient);
  list() { return this.http.get<ProjectSummary[]>('/api/projects'); }
  get(id: string) { return this.http.get<Project>(`/api/projects/${id}`); }
  create(data: ProjectInput) { return this.http.post<Project>('/api/projects', data); }
  update(id: string, data: ProjectInput) { return this.http.patch<Project>(`/api/projects/${id}`, data); }
}

export function errorMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (error.status === 404) return 'Проект не найден. Вернитесь к списку проектов.';
    if (error.status === 422) return 'Проверьте поля: название до 200 символов, требования до 50 000. Оба поля обязательны.';
  }
  return 'Не удалось связаться с сервером. Попробуйте ещё раз.';
}
