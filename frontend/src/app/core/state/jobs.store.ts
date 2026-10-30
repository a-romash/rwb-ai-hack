import {DestroyRef, effect, inject, Injectable, signal} from '@angular/core';
import {Observable, map, tap} from 'rxjs';
import {JobAssumption, JobRead, JobUsage} from '../api/api.types';
import {readableError} from '../api/errors';
import {StudioApi} from '../api/projects.api';
import {jobStatusView} from '../pipeline/status';
import {readJson, writeJson} from '../util/storage';

/**
 * Запуск агента в истории браузера. У бэкенда нет списка задач проекта,
 * поэтому история хранится локально, а статус каждой задачи опрашивается у API.
 */
export interface JobRecord {
  id: string;
  projectId: string;
  agent: string;
  stageKey: string | null;
  prompt: string;
  promptLength: number;
  createdAt: number;
  updatedAt: number;
  finishedAt: number | null;
  status: string;
  subtype: string | null;
  result: string | null;
  numTurns: number | null;
  usage?: JobUsage;
  durationMs?: number;
  assumptions?: JobAssumption[];
  /** Очередь долго не возвращает статус. */
  stale?: boolean;
  /** Результат в Celery истёк (хранится час) — показываем сохранённый. */
  expired?: boolean;
  /** Опрос остановлен из-за ошибок сети. */
  lastError?: string | null;
}

export interface StartJob {
  agent: string;
  prompt: string | null;
  stageKey: string | null;
}

const STORAGE_KEY = 'potok.jobs.v1';
const MAX_PER_PROJECT = 40;
const STORED_PROMPT = 4000;
const STORED_RESULT = 60_000;
const STALE_AFTER_MS = 20 * 60_000;

function nextDelay(ageMs: number): number {
  if (ageMs < 30_000) return 1500;
  if (ageMs < 180_000) return 3000;
  return 6000;
}

@Injectable({providedIn: 'root'})
export class JobsStore {
  private readonly api = inject(StudioApi);
  private readonly records = signal<Record<string, JobRecord[]>>(readJson(STORAGE_KEY, {}));
  private readonly timers = new Map<string, ReturnType<typeof setTimeout>>();
  private readonly failures = new Map<string, number>();

  constructor() {
    effect(() => writeJson(STORAGE_KEY, this.records()));
    inject(DestroyRef).onDestroy(() => this.timers.forEach(clearTimeout));
  }

  /** Запуски проекта, новые сверху. Читает signal, поэтому реактивно в шаблонах и computed. */
  list(projectId: string): JobRecord[] {
    return this.records()[projectId] ?? [];
  }

  /** Последний запуск по каждому этапу. */
  latestByStage(projectId: string): Map<string, JobRecord> {
    const latest = new Map<string, JobRecord>();
    for (const record of this.list(projectId)) {
      if (record.stageKey && !latest.has(record.stageKey)) latest.set(record.stageKey, record);
    }
    return latest;
  }

  start(projectId: string, job: StartJob): Observable<JobRecord> {
    const body = job.prompt ? {agent: job.agent, prompt: job.prompt} : {agent: job.agent};
    return this.api.createJob(projectId, body).pipe(
      map(created => {
        const now = Date.now();
        const prompt = job.prompt ?? '';
        const record: JobRecord = {
          id: created.id,
          projectId,
          agent: created.agent ?? job.agent,
          stageKey: job.stageKey,
          prompt: prompt.slice(0, STORED_PROMPT),
          promptLength: prompt.length,
          createdAt: now,
          updatedAt: now,
          finishedAt: null,
          status: created.status || 'queued',
          subtype: null,
          result: null,
          numTurns: null,
        };
        return record;
      }),
      tap(record => {
        this.records.update(all => ({
          ...all,
          [projectId]: [record, ...(all[projectId] ?? [])].slice(0, MAX_PER_PROJECT),
        }));
        this.schedule(projectId, record.id, 900);
      }),
    );
  }

  /** Возобновляет опрос незавершённых запусков проекта: после перезагрузки страницы или возврата в проект. */
  resume(projectId: string): void {
    for (const record of this.list(projectId)) {
      const view = jobStatusView(record.status, record.subtype, record.stale);
      if (!view.terminal && !this.timers.has(record.id) && !record.lastError) {
        this.schedule(projectId, record.id, 300);
      }
    }
  }

  /** Ручная проверка статуса: снимает признаки «нет статуса» и «нет связи». */
  refresh(projectId: string, jobId: string): void {
    this.failures.delete(jobId);
    this.patch(projectId, jobId, {stale: false, lastError: null});
    this.schedule(projectId, jobId, 0);
  }

  remove(projectId: string, jobId: string): void {
    this.stop(jobId);
    this.records.update(all => ({...all, [projectId]: (all[projectId] ?? []).filter(record => record.id !== jobId)}));
  }

  private schedule(projectId: string, jobId: string, delay: number): void {
    this.stop(jobId);
    this.timers.set(jobId, setTimeout(() => this.fetch(projectId, jobId), delay));
  }

  private stop(jobId: string): void {
    const timer = this.timers.get(jobId);
    if (timer) clearTimeout(timer);
    this.timers.delete(jobId);
  }

  private fetch(projectId: string, jobId: string): void {
    this.timers.delete(jobId);
    const before = this.find(projectId, jobId);
    if (!before) return;
    this.api.getJob(projectId, jobId).subscribe({
      next: job => {
        this.failures.delete(jobId);
        const record = this.merge(projectId, before, job);
        const view = jobStatusView(record.status, record.subtype, record.stale);
        if (view.terminal) return;
        const age = Date.now() - record.createdAt;
        if (view.phase === 'queued' && age > STALE_AFTER_MS) {
          this.patch(projectId, jobId, {stale: true});
          return;
        }
        this.schedule(projectId, jobId, nextDelay(age));
      },
      error: error => {
        const count = (this.failures.get(jobId) ?? 0) + 1;
        this.failures.set(jobId, count);
        if (count >= 6) {
          this.patch(projectId, jobId, {lastError: readableError(error, 'job').title});
          return;
        }
        this.schedule(projectId, jobId, Math.min(15_000, 2000 * count));
      },
    });
  }

  private merge(projectId: string, before: JobRecord, job: JobRead): JobRecord {
    const status = job.status.toLowerCase();
    const wasTerminal = jobStatusView(before.status, before.subtype).terminal;
    // Celery отдаёт pending для неизвестной задачи: после истечения результата не откатываем готовый статус.
    if (wasTerminal && status === 'pending') {
      return this.patch(projectId, before.id, {expired: true}) ?? before;
    }
    const terminal = jobStatusView(status, job.subtype ?? null).terminal;
    return (
      this.patch(projectId, before.id, {
        status,
        subtype: job.subtype ?? null,
        result: job.result ? job.result.slice(0, STORED_RESULT) : before.result,
        numTurns: job.num_turns ?? before.numTurns,
        usage: job.usage ?? before.usage,
        durationMs: job.duration_ms ?? job.usage?.duration_ms ?? before.durationMs,
        assumptions: job.assumptions ?? before.assumptions,
        finishedAt: terminal ? before.finishedAt ?? Date.now() : null,
        stale: false,
        lastError: null,
      }) ?? before
    );
  }

  private find(projectId: string, jobId: string): JobRecord | undefined {
    return this.list(projectId).find(record => record.id === jobId);
  }

  private patch(projectId: string, jobId: string, changes: Partial<JobRecord>): JobRecord | undefined {
    let updated: JobRecord | undefined;
    this.records.update(all => {
      const list = all[projectId] ?? [];
      return {
        ...all,
        [projectId]: list.map(record => {
          if (record.id !== jobId) return record;
          updated = {...record, ...changes, updatedAt: Date.now()};
          return updated;
        }),
      };
    });
    return updated;
  }
}
