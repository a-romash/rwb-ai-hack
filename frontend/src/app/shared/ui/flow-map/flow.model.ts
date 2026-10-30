import {Stage} from '../../../core/api/api.types';
import {PhaseKey, STAGE_CATALOG, stageInfo} from '../../../core/pipeline/stages.catalog';
import {jobStatusView, stageStatusView, Tone} from '../../../core/pipeline/status';
import {JobRecord} from '../../../core/state/jobs.store';

/** Станция на линии этапов: место, подпись и статус. */
export interface FlowStation {
  key: string;
  label: string;
  phase: PhaseKey;
  column: number;
  lane: number;
  position: number;
  tone: Tone;
  statusLabel: string;
  live: boolean;
  /** Статус взят из запуска агента в этом браузере, а не из этапа на сервере. */
  fromJob: boolean;
}

/**
 * Собирает станции из этапов проекта и последних запусков агентов.
 * Этапы, которых нет в справочнике, встают в конец линии отдельными колонками.
 */
export function buildStations(stages: readonly Stage[], latest: Map<string, JobRecord> = new Map()): FlowStation[] {
  const known = STAGE_CATALOG.length ? Math.max(...STAGE_CATALOG.map(stage => stage.column)) : 0;
  let extra = known;
  return [...stages]
    .sort((a, b) => a.position - b.position)
    .map(stage => {
      const info = stageInfo(stage.key);
      const job = latest.get(stage.key);
      const status = job ? jobStatusView(job.status, job.subtype, job.stale) : stageStatusView(stage.status);
      return {
        key: stage.key,
        label: info?.short ?? stage.name,
        phase: info?.phase ?? 'delivery',
        column: info ? info.column : ++extra,
        lane: info?.lane ?? 0,
        position: stage.position,
        tone: status.tone,
        statusLabel: status.label,
        live: status.live,
        fromJob: Boolean(job),
      };
    });
}

/** Станции без проекта: для пустых состояний и превью. */
export function previewStations(): FlowStation[] {
  return STAGE_CATALOG.map((info, index) => ({
    key: info.key,
    label: info.short,
    phase: info.phase,
    column: info.column,
    lane: info.lane,
    position: index + 1,
    tone: 'idle' as Tone,
    statusLabel: 'Не запущен',
    live: false,
    fromJob: false,
  }));
}

/** Порядок обхода: по колонкам, внутри колонки — сверху вниз. */
export function byPlace(a: FlowStation, b: FlowStation): number {
  return a.column - b.column || a.lane - b.lane || a.position - b.position;
}

/** Есть ли у этапа исполнитель-агент. */
export function hasAgent(station: FlowStation): boolean {
  return Boolean(stageInfo(station.key)?.agent);
}

/** Вторая строка узла: статус запуска, а у нетронутого этапа — есть ли у него агент. */
export function stationNote(station: FlowStation): string {
  if (station.tone === 'idle' && !station.fromJob) return hasAgent(station) ? 'Не запускался' : 'Без агента';
  return station.statusLabel;
}

/** Иконка статуса: одна и та же в графе, таблицах и бейджах. */
export function toneIcon(tone: Tone, live = false): string {
  if (live) return '@tui.loader-circle';
  switch (tone) {
    case 'ok':
      return '@tui.circle-check';
    case 'fail':
      return '@tui.circle-x';
    case 'wait':
      return '@tui.circle-alert';
    case 'run':
      return '@tui.clock';
    default:
      return '@tui.circle-dashed';
  }
}

/**
 * Ортогональная связь со скруглёнными углами: вправо до шины xm, вдоль неё по вертикали, дальше вправо.
 * Связи, идущие через одну шину, сливаются в аккуратную развилку.
 */
export function connector(x1: number, y1: number, x2: number, y2: number, xm: number, radius = 8): string {
  if (Math.abs(y2 - y1) < 0.5) return `M${x1} ${y1}H${x2}`;
  const dir = y2 > y1 ? 1 : -1;
  const r = Math.max(0, Math.min(radius, Math.abs(y2 - y1) / 2, xm - x1, x2 - xm));
  return (
    `M${x1} ${y1}H${xm - r}` +
    `Q${xm} ${y1} ${xm} ${y1 + dir * r}` +
    `V${y2 - dir * r}` +
    `Q${xm} ${y2} ${xm + r} ${y2}` +
    `H${x2}`
  );
}
