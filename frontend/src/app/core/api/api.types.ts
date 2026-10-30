/**
 * Типы ответов бэкенда (`backend/app/schemas.py`).
 * Поля, которых бэкенд пока не отдаёт, необязательны и описаны в CONTRACT.md.
 */

/** Сейчас бэкенд отдаёт только `not_started`; остальные значения — из архитектуры прогона (waiting_*, частичный результат). */
export type StageStatus =
  | 'not_started'
  | 'queued'
  | 'running'
  | 'waiting_input'
  | 'succeeded'
  | 'partial'
  | 'failed'
  | 'skipped';

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
  status: StageStatus;
}

export interface Project extends ProjectSummary {
  requirements: string;
  stages: Stage[];
}

export interface ProjectInput {
  name: string;
  requirements: string;
}

export type ProjectPatch = Partial<ProjectInput>;

export interface JobCreate {
  agent: string;
  /** Если не передан, бэкенд берёт требования проекта. */
  prompt?: string;
}

/** Расход по данным харнесса агента. Бэкенд считает, но пока не отдаёт (CONTRACT.md). */
export interface JobUsage {
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  reasoning_tokens?: number;
  cached_tokens?: number;
  attempts?: number;
  duration_ms?: number;
}

export interface JobAssumption {
  question: string;
  answer: string;
}

/**
 * Состояние задачи агента. `status` — состояние Celery в нижнем регистре
 * (`pending`, `started`, `success`, `failure`, `retry`, `revoked`) или `queued` сразу после постановки.
 * `subtype` — итог харнесса: `success`, `partial`, `blocked`, `budget`, `error`, `error_max_turns`, `unfinished`, `no_progress`.
 */
export interface JobRead {
  id: string;
  status: string;
  agent: string | null;
  subtype: string | null;
  result: string | null;
  num_turns: number | null;
  usage?: JobUsage;
  duration_ms?: number;
  assumptions?: JobAssumption[];
}

export interface Health {
  status: 'ok';
}
