import {GateKey, GATES, normalizeStageKey, STAGE_CATALOG, StageInfo, StageKey} from '../../../core/pipeline/stages.catalog';
import {jobStatusView, Tone, toneIcon} from '../../../core/pipeline/status';
import {JobRecord} from '../../../core/state/jobs.store';

/** Шаг конвейера RWB со статусом последнего запуска агента для него. */
export interface PipelineStage {
  kind: 'stage';
  /** Ключ выбора в интерфейсе: у шага — его ключ. */
  id: string;
  key: StageKey;
  code: string;
  title: string;
  position: number;
  tone: Tone;
  statusLabel: string;
  live: boolean;
  /** Статус взят из запуска агента в этом браузере. */
  fromJob: boolean;
  icon: string;
  info: StageInfo;
}

/** Ворота качества после шага. Результатов проверки у API пока нет: они придут с прогонами. */
export interface PipelineGate {
  kind: 'gate';
  /** Ключ выбора в интерфейсе: `gate:G0`. */
  id: string;
  key: GateKey;
  name: string;
  stageKey: StageKey;
  tone: Tone;
  statusLabel: string;
  icon: string;
}

export type PipelineItem = PipelineStage | PipelineGate;

/**
 * Шаги конвейера со статусами последних запусков агентов. Запуски — новые сверху.
 * Старые запуски, привязанные к этапам проекта, попадают на шаг, где этап участвует.
 */
export function buildPipeline(runs: readonly JobRecord[] = []): PipelineStage[] {
  const latest = new Map<StageKey, JobRecord>();
  for (const run of runs) {
    const key = normalizeStageKey(run.stageKey);
    if (key && !latest.has(key)) latest.set(key, run);
  }
  return STAGE_CATALOG.map((info, index) => {
    const run = latest.get(info.key);
    const view = run ? jobStatusView(run.status, run.subtype, run.stale) : null;
    const tone: Tone = view?.tone ?? 'idle';
    const live = view?.live ?? false;
    return {
      kind: 'stage',
      id: info.key,
      key: info.key,
      code: info.code,
      title: info.title,
      position: index + 1,
      tone,
      statusLabel: view?.label ?? (info.agent ? 'Не запускался' : 'Без агента'),
      live,
      fromJob: Boolean(run),
      icon: toneIcon(tone, live),
      info,
    };
  });
}

/** Шаги и ворота по порядку прохождения: ворота стоят сразу после своего шага. */
export function pipelineItems(stages: readonly PipelineStage[]): PipelineItem[] {
  return stages.flatMap(stage => [stage, ...stage.info.gates.map(key => gateItem(key, stage.key))]);
}

export function gateItem(key: GateKey, stageKey: StageKey): PipelineGate {
  return {
    kind: 'gate',
    id: `gate:${key}`,
    key,
    name: GATES[key].name,
    stageKey,
    tone: 'idle',
    statusLabel: 'Не проверялись',
    icon: '@tui.shield',
  };
}

/** Последний запуск агента для шага. */
export function latestRun(runs: readonly JobRecord[], key: StageKey): JobRecord | null {
  return runs.find(run => normalizeStageKey(run.stageKey) === key) ?? null;
}
