import {StageStatus} from '../api/api.types';

/** Тон статуса — единственный источник насыщенного цвета в интерфейсе. */
export type Tone = 'idle' | 'run' | 'wait' | 'ok' | 'fail';

export interface StatusView {
  tone: Tone;
  label: string;
  /** Процесс идёт: показываем пульсацию и опрашиваем сервер. */
  live: boolean;
}

const STAGE_STATUS: Record<StageStatus, StatusView> = {
  not_started: {tone: 'idle', label: 'Не запущен', live: false},
  queued: {tone: 'run', label: 'В очереди', live: true},
  running: {tone: 'run', label: 'Выполняется', live: true},
  waiting_input: {tone: 'wait', label: 'Ждёт ответа', live: false},
  succeeded: {tone: 'ok', label: 'Готово', live: false},
  partial: {tone: 'wait', label: 'Частично', live: false},
  failed: {tone: 'fail', label: 'Ошибка', live: false},
  skipped: {tone: 'idle', label: 'Пропущен', live: false},
};

export function stageStatusView(status: string): StatusView {
  return STAGE_STATUS[status as StageStatus] ?? {tone: 'idle', label: status, live: false};
}

/** Фаза задачи агента: состояние Celery плюс итог харнесса. */
export type JobPhase = 'queued' | 'running' | 'done' | 'partial' | 'blocked' | 'failed' | 'stale';

export interface JobStatusView extends StatusView {
  phase: JobPhase;
  terminal: boolean;
  /** Пояснение под статусом: почему агент остановился. */
  hint: string;
}

const SUBTYPE: Record<string, Omit<JobStatusView, 'live' | 'terminal'>> = {
  success: {phase: 'done', tone: 'ok', label: 'Готово', hint: 'Агент завершил работу.'},
  partial: {phase: 'partial', tone: 'wait', label: 'Частично', hint: 'Время на задачу вышло. Результат неполный.'},
  budget: {phase: 'partial', tone: 'wait', label: 'Бюджет исчерпан', hint: 'Агент упёрся в лимит токенов. Результат неполный.'},
  blocked: {phase: 'blocked', tone: 'wait', label: 'Нужен ответ', hint: 'Агенту нужен ответ аналитика, чтобы продолжить.'},
  error_max_turns: {phase: 'failed', tone: 'fail', label: 'Лимит шагов', hint: 'Агент исчерпал число шагов и не завершил задачу.'},
  unfinished: {phase: 'failed', tone: 'fail', label: 'Не завершено', hint: 'Агент остановился, не вызвав завершение задачи.'},
  no_progress: {phase: 'failed', tone: 'fail', label: 'Нет прогресса', hint: 'Несколько попыток подряд дали тот же результат. Изменения откатаны.'},
  error: {phase: 'failed', tone: 'fail', label: 'Ошибка агента', hint: 'Агент не смог выполнить задачу. Подробности — в результате.'},
};

export function jobStatusView(status: string, subtype: string | null, stale = false): JobStatusView {
  const state = status.toLowerCase();
  if (stale) {
    return {phase: 'stale', tone: 'idle', label: 'Нет статуса', live: false, terminal: true, hint: 'Очередь долго не отвечает. Проверьте worker: docker compose logs worker.'};
  }
  if (state === 'queued' || state === 'pending' || state === 'received') {
    return {phase: 'queued', tone: 'run', label: 'В очереди', live: true, terminal: false, hint: 'Задача ждёт свободного worker.'};
  }
  if (state === 'started' || state === 'retry') {
    return {phase: 'running', tone: 'run', label: 'Выполняется', live: true, terminal: false, hint: 'Агент работает. Статус обновляется автоматически.'};
  }
  if (state === 'success') {
    const view = SUBTYPE[subtype ?? 'success'] ?? SUBTYPE['success'];
    return {...view, live: false, terminal: true};
  }
  if (state === 'revoked') {
    return {phase: 'failed', tone: 'idle', label: 'Отменено', live: false, terminal: true, hint: 'Задача отменена в очереди.'};
  }
  return {phase: 'failed', tone: 'fail', label: 'Сбой задачи', live: false, terminal: true, hint: 'Задача упала в worker. Подробности — в docker compose logs worker.'};
}

/** Иконка статуса: одна и та же в конвейере, таблицах и бейджах. */
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
