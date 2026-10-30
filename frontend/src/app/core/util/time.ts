import {plural} from './text';

const TIME = new Intl.DateTimeFormat('ru-RU', {hour: '2-digit', minute: '2-digit'});
const DATE = new Intl.DateTimeFormat('ru-RU', {day: 'numeric', month: 'long'});
const DATE_YEAR = new Intl.DateTimeFormat('ru-RU', {day: 'numeric', month: 'long', year: 'numeric'});
const FULL = new Intl.DateTimeFormat('ru-RU', {day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'});

function startOfDay(ms: number): number {
  const d = new Date(ms);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

/** «только что», «5 минут назад», «сегодня в 14:20», «вчера в 09:05», «3 октября». */
export function relativeTime(value: string | number | Date, now: number): string {
  const ms = new Date(value).getTime();
  if (Number.isNaN(ms)) return '';
  const diff = Math.max(0, now - ms);
  const minutes = Math.floor(diff / 60_000);
  if (diff < 45_000) return 'только что';
  if (minutes < 60) {
    const m = Math.max(1, minutes);
    return `${m} ${plural(m, ['минуту', 'минуты', 'минут'])} назад`;
  }
  const today = startOfDay(now);
  if (ms >= today) return `сегодня в ${TIME.format(ms)}`;
  if (ms >= today - 86_400_000) return `вчера в ${TIME.format(ms)}`;
  const sameYear = new Date(ms).getFullYear() === new Date(now).getFullYear();
  return sameYear ? DATE.format(ms) : DATE_YEAR.format(ms);
}

export function fullDate(value: string | number | Date): string {
  const ms = new Date(value).getTime();
  return Number.isNaN(ms) ? '' : FULL.format(ms);
}

/** «42 с», «3 мин 05 с», «1 ч 12 мин». */
export function formatDuration(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h) return `${h} ч ${String(m).padStart(2, '0')} мин`;
  if (m) return `${m} мин ${String(s).padStart(2, '0')} с`;
  return `${s} с`;
}
