/** Русские формы множественного числа: 1 этап, 2 этапа, 5 этапов. */
export function plural(n: number, forms: readonly [string, string, string]): string {
  const abs = Math.abs(n) % 100;
  const last = abs % 10;
  if (abs > 10 && abs < 20) return forms[2];
  if (last > 1 && last < 5) return forms[1];
  if (last === 1) return forms[0];
  return forms[2];
}

const NUMBER = new Intl.NumberFormat('ru-RU');

export function formatNumber(n: number): string {
  return NUMBER.format(n);
}

export function countWords(text: string): number {
  const matches = text.trim().match(/[\p{L}\p{N}][\p{L}\p{N}'’-]*/gu);
  return matches ? matches.length : 0;
}

/**
 * Грубая оценка числа токенов для Qwen: в русском тексте около 3,2 символа на токен.
 * Это подсказка порядка величины, а не счёт токенизатора.
 */
export function estimateTokens(text: string): number {
  return Math.ceil(text.trim().length / 3.2);
}

export function clip(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max - 1).trimEnd()}…`;
}
