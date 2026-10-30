import {computed, DestroyRef, inject, Injectable, signal} from '@angular/core';
import {Observable, tap} from 'rxjs';
import {ArtifactRead, AttachmentRead, Autonomy, Project, ProjectPatch, RunRead} from '../../core/api/api.types';
import {readableError, ReadableError} from '../../core/api/errors';
import {StudioApi} from '../../core/api/projects.api';
import {jobStatusView, runStatusView} from '../../core/pipeline/status';
import {JobRecord, JobsStore, StartJob} from '../../core/state/jobs.store';
import {ProjectsStore} from '../../core/state/projects.store';
import {buildPipeline, buildRunPipeline, pipelineItems} from '../../shared/ui/pipeline/pipeline.model';

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
  /** Последний прогон конвейера проекта (`/runs`); без него шаги показывают запуски агентов. */
  readonly pipelineRun = signal<RunRead | null>(null);
  readonly artifacts = signal<ArtifactRead[]>([]);
  readonly attachments = signal<AttachmentRead[]>([]);
  readonly pipelineView = computed(() => {
    const run = this.pipelineRun();
    return run ? runStatusView(run.status) : null;
  });
  private events: EventSource | null = null;
  private refetch: ReturnType<typeof setTimeout> | null = null;

  /** Шаги конвейера RWB: статусы этапов прогона или, без прогона, последних запусков агентов. */
  readonly stages = computed(() => {
    const run = this.pipelineRun();
    return run ? buildRunPipeline(run) : buildPipeline(this.runs());
  });
  /** Шаги и ворота качества по порядку прохождения. */
  readonly items = computed(() => pipelineItems(this.stages()));
  readonly liveRuns = computed(() => this.runs().filter(run => jobStatusView(run.status, run.subtype, run.stale).live).length);

  constructor() {
    inject(DestroyRef).onDestroy(() => this.follow(null));
  }

  open(id: string): void {
    if (this.id() === id && this.project()) return;
    this.id.set(id);
    this.project.set(null);
    this.pipelineRun.set(null);
    this.artifacts.set([]);
    this.attachments.set([]);
    this.follow(null);
    this.load();
    this.api.attachments(id).subscribe({next: files => this.id() === id && this.attachments.set(files), error: () => undefined});
    this.jobs.resume(id);
    this.api.listRuns(id).subscribe({
      next: runs => {
        const latest = [...runs].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
        if (latest && this.id() === id) this.follow(latest.id);
      },
      error: () => this.pipelineRun.set(null),
    });
  }

  attach(file: File): Observable<AttachmentRead> {
    return this.api.uploadAttachment(this.id() as string, file).pipe(
      tap(saved => this.attachments.update(files => [...files.filter(f => f.name !== saved.name), saved].sort((a, b) => a.name.localeCompare(b.name)))),
    );
  }

  /** Запуск всего конвейера: этапы идут друг за другом в воркерах, Студия следит по SSE. */
  startRun(autonomy: Autonomy, budget: {tokens: number; minutes: number}): Observable<RunRead> {
    return this.api.createRun(this.id() as string, {autonomy, budget}).pipe(tap(run => this.follow(run.id, run)));
  }

  retryStage(key: string): Observable<unknown> {
    return this.api.retryStage(this.pipelineRun()!.id, key).pipe(tap(() => this.reloadRun()));
  }

  answer(answers: Record<string, string>): Observable<unknown> {
    return this.api.answer(this.pipelineRun()!.id, answers).pipe(tap(() => this.reloadRun()));
  }

  decide(gate: string, decision: 'approve' | 'reject', comment = ''): Observable<unknown> {
    return this.api.decide(this.pipelineRun()!.id, gate, decision, comment).pipe(tap(() => this.reloadRun()));
  }

  cancelRun(): Observable<unknown> {
    return this.api.cancelRun(this.pipelineRun()!.id).pipe(tap(() => this.reloadRun()));
  }

  fileUrl(path: string): string {
    return this.api.fileUrl(this.pipelineRun()!.id, path);
  }

  /** Подписка на события прогона: каждое событие — повод перечитать снимок (не чаще раза в 400 мс). */
  private follow(runId: string | null, snapshot?: RunRead): void {
    this.events?.close();
    this.events = null;
    if (this.refetch) clearTimeout(this.refetch);
    if (!runId) return;
    if (snapshot) this.pipelineRun.set(snapshot);
    this.reloadRun(runId);
    const events = this.api.runEvents(runId);
    // Типы событий раннера (backend/app/runner.py::_event); у SSE они приходят в поле event.
    for (const type of ['stage.queued', 'stage.started', 'stage.finished', 'gate.result', 'question.asked', 'run.retry', 'run.finished']) {
      events.addEventListener(type, () => this.scheduleReload(runId));
    }
    this.events = events;
  }

  private scheduleReload(runId: string): void {
    if (this.refetch) return;
    this.refetch = setTimeout(() => {
      this.refetch = null;
      this.reloadRun(runId);
    }, 400);
  }

  private reloadRun(runId = this.pipelineRun()?.id): void {
    if (!runId) return;
    this.api.getRun(runId).subscribe({
      next: run => {
        if (run.project_id !== this.id()) return;
        this.pipelineRun.set(run);
        if (!runStatusView(run.status).live) this.events?.close();
      },
    });
    this.api.artifacts(runId).subscribe({next: artifacts => this.artifacts.set(artifacts), error: () => undefined});
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
