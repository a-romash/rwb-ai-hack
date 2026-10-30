import {GateKey, GATES, normalizeStageKey, STAGE_CATALOG, StageInfo, StageKey} from '../../../core/pipeline/stages.catalog';
import {GateResult, RunRead, StageRunRead} from '../../../core/api/api.types';
import {jobStatusView, stageStatusView, Tone, toneIcon} from '../../../core/pipeline/status';
import {JobRecord} from '../../../core/state/jobs.store';
import {plural} from '../../../core/util/text';

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
  /** Этап прогона конвейера, если статус взят из прогона. */
  stageRun?: StageRunRead;
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
  /** Результат проверки в прогоне конвейера. */
  result?: GateResult;
  /** Этап ждёт решения человека по этим воротам (A0/A1). */
  waiting?: boolean;
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

/** Шаги со статусами этапов прогона конвейера (`RunRead.stages`); этапы, до которых прогон не дошёл, ждут. */
export function buildRunPipeline(run: RunRead): PipelineStage[] {
  const byKey = new Map(run.stages.map(stage => [stage.key, stage]));
  return STAGE_CATALOG.map((info, index) => {
    const stageRun = byKey.get(info.key);
    const view = stageStatusView(stageRun?.status ?? 'pending');
    return {
      kind: 'stage',
      id: info.key,
      key: info.key,
      code: info.code,
      title: info.title,
      position: index + 1,
      tone: view.tone,
      statusLabel: stageRun && stageRun.attempt > 1 ? `${view.label}, попытка ${stageRun.attempt}` : view.label,
      live: view.live,
      fromJob: false,
      stageRun,
      icon: toneIcon(view.tone, view.live),
      info,
    };
  });
}

/** Шаги и ворота по порядку прохождения: ворота стоят сразу после своего шага. */
export function pipelineItems(stages: readonly PipelineStage[]): PipelineItem[] {
  return stages.flatMap(stage => [
    stage,
    ...stage.info.gates.map(key =>
      gateItem(key, stage.key, stage.stageRun?.gate?.gate === key ? stage.stageRun.gate : undefined, stage.stageRun?.status === 'waiting_human'),
    ),
  ]);
}

export function gateItem(key: GateKey, stageKey: StageKey, result?: GateResult, waiting = false): PipelineGate {
  const errors = result?.findings.filter(finding => finding.severity === 'error').length ?? 0;
  const tone: Tone = waiting ? 'wait' : !result ? 'idle' : result.passed ? 'ok' : 'fail';
  return {
    kind: 'gate',
    id: `gate:${key}`,
    key,
    name: GATES[key].name,
    stageKey,
    tone,
    statusLabel: waiting
      ? 'Ждёт решения'
      : !result
        ? 'Не проверялись'
        : result.passed
          ? result.decided_by === 'human' ? 'Принято человеком' : 'Пройдены'
          : `Не пройдены: ${errors} ${plural(errors, ['ошибка', 'ошибки', 'ошибок'])}`,
    icon: tone === 'idle' ? '@tui.shield' : toneIcon(tone),
    result,
    waiting,
  };
}

/** Последний запуск агента для шага. */
export function latestRun(runs: readonly JobRecord[], key: StageKey): JobRecord | null {
  return runs.find(run => normalizeStageKey(run.stageKey) === key) ?? null;
}
