import {computed, inject, Injectable, signal} from '@angular/core';
import {Observable, tap} from 'rxjs';
import {Project, ProjectPatch} from '../../core/api/api.types';
import {readableError, ReadableError} from '../../core/api/errors';
import {StudioApi} from '../../core/api/projects.api';
import {jobStatusView} from '../../core/pipeline/status';
import {JobRecord, JobsStore, StartJob} from '../../core/state/jobs.store';
import {ProjectsStore} from '../../core/state/projects.store';
import {buildPipeline, pipelineItems} from '../../shared/ui/pipeline/pipeline.model';

/** Состояние открытого проекта. Живёт столько же, сколько экран проекта, и общее для его вкладок. */
@Injectable()
export class WorkspaceStore {
  private readonly api = inject(StudioApi);
  private readonly projects = inject(ProjectsStore);
  private readonly jobs = inject(JobsStore);

  readonly id = signal<string | null>(null);
  readonly project = signal<Project | null>(null);
  readonly state = signal<'loading' | 'ready' | 'error'>('loading');
  readonly error = signal<ReadableError | null>(null);

  readonly runs = computed<JobRecord[]>(() => {
    const id = this.id();
    return id ? this.jobs.list(id) : [];
  });
  /** Шаги конвейера RWB со статусами последних запусков агентов. */
  readonly stages = computed(() => buildPipeline(this.runs()));
  /** Шаги и ворота качества по порядку прохождения. */
  readonly items = computed(() => pipelineItems(this.stages()));
  readonly liveRuns = computed(() => this.runs().filter(run => jobStatusView(run.status, run.subtype, run.stale).live).length);

  open(id: string): void {
    if (this.id() === id && this.project()) return;
    this.id.set(id);
    this.project.set(null);
    this.load();
    this.jobs.resume(id);
  }

  load(): void {
    const id = this.id();
    if (!id) return;
    this.state.set('loading');
    this.error.set(null);
    this.api.getProject(id).subscribe({
      next: project => {
        if (this.id() !== id) return;
        this.project.set(project);
        this.state.set('ready');
        this.projects.upsert(project);
      },
      error: error => {
        if (this.id() !== id) return;
        this.error.set(readableError(error, 'project'));
        this.state.set('error');
      },
    });
  }

  save(patch: ProjectPatch): Observable<Project> {
    const id = this.id() as string;
    return this.api.updateProject(id, patch).pipe(
      tap(project => {
        this.project.set(project);
        this.projects.upsert(project);
      }),
    );
  }

  start(job: StartJob): Observable<JobRecord> {
    return this.jobs.start(this.id() as string, job);
  }

  refresh(jobId: string): void {
    this.jobs.refresh(this.id() as string, jobId);
  }

  remove(jobId: string): void {
    this.jobs.remove(this.id() as string, jobId);
  }
}
