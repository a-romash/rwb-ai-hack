/**
 * Типы ответов бэкенда (`backend/app/schemas.py`).
 * Поля, которых бэкенд пока не отдаёт, необязательны и описаны в CONTRACT.md.
 */

/** Статус этапа: `contracts/api.py` StageStatus плюс значения старого API проекта (`not_started`, `partial`). */
export type StageStatus =
  | 'not_started'
  | 'pending'
  | 'queued'
  | 'running'
  | 'waiting_input'
  | 'waiting_human'
  | 'succeeded'
  | 'partial'
  | 'failed'
  | 'skipped'
  | 'stale';

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

/* Прогон конвейера (`contracts/api.py`, роутер `backend/app/runs.py`). */

export type Autonomy = 'A0' | 'A1' | 'A2';
export type RunStatus = 'pending' | 'running' | 'waiting' | 'succeeded' | 'partial' | 'failed' | 'cancelled';

export interface RunCreate {
  autonomy?: Autonomy;
  budget?: {tokens?: number; minutes?: number};
}

export interface GateFinding {
  path: string;
  code: string;
  severity: 'error' | 'warning';
  message: string;
}

export interface GateResult {
  gate: string;
  passed: boolean;
  decided_by: 'code' | 'human';
  findings: GateFinding[];
}

export interface StageRunRead {
  key: string;
  title: string;
  rwb_stage: string;
  participants: string[];
  status: StageStatus;
  attempt: number;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  summary: string | null;
  gate: GateResult | null;
}

export interface RunQuestion {
  id: string;
  text: string;
  options: string[];
  default: string;
  why: string;
  blocking?: boolean;
}

export interface RunSummary {
  id: string;
  project_id: string;
  status: RunStatus;
  autonomy: Autonomy;
  spec_version: number;
  created_at: string;
  finished_at: string | null;
}

export interface RunRead extends RunSummary {
  prototype_url?: string | null;
  budget: {tokens_used: number | null; tokens_limit: number; minutes_used: number; minutes_limit: number};
  stages: StageRunRead[];
  flags: {path: string; status: string; reason: string; gate: string | null}[];
  questions: RunQuestion[];
}

/** Файл аналитика к проекту: следующий прогон получит его в input/. */
export interface AttachmentRead {
  name: string;
  size: number;
}

export interface ArtifactRead {
  name: string;
  path: string;
  stage: string;
  hash: string;
  size: number;
  kind: 'json' | 'markdown' | 'dir' | 'text';
}
