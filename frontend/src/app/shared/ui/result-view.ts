import {ChangeDetectionStrategy, Component, computed, input, signal} from '@angular/core';
import {TuiButton} from '@taiga-ui/core';

type Token = {kind: 'key' | 'string' | 'number' | 'literal' | 'punct' | 'space'; text: string};

interface Parsed {
  /** Текст резюме, если агент вернул объект с полем summary. */
  summary: string | null;
  json: Token[] | null;
  plain: string;
}

const COLLAPSE_LINES = 16;

/**
 * Результат агента: резюме читается как текст, JSON подсвечивается, остальное — как есть.
 * Без innerHTML: подсветка собирается из токенов, поэтому вывод агента не исполняется.
 */
@Component({
  selector: 'app-result-view',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiButton],
  template: `
    @let view = parsed();
    @if (view.summary !== null && !showJson()) {
      <div class="summary" [class.clamped]="clamped()">{{ view.summary }}</div>
    } @else if (view.json) {
      <pre class="code" [class.clamped]="clamped()"><code>@for (token of view.json; track $index) {<span [class]="token.kind">{{ token.text }}</span>}</code></pre>
    } @else {
      <pre class="plain" [class.clamped]="clamped()">{{ view.plain }}</pre>
    }
    <div class="actions">
      @if (long()) {
        <button tuiButton type="button" appearance="flat" size="xs" (click)="expanded.set(!expanded())">
          {{ expanded() ? 'Свернуть' : 'Показать полностью' }}
        </button>
      }
      @if (view.summary !== null && view.json) {
        <button tuiButton type="button" appearance="flat" size="xs" (click)="showJson.set(!showJson())">
          {{ showJson() ? 'Показать резюме' : 'Показать JSON' }}
        </button>
      }
      <button tuiButton type="button" appearance="flat" size="xs" iconStart="@tui.copy" (click)="copy()">
        {{ copied() ? 'Скопировано' : 'Копировать' }}
      </button>
    </div>
  `,
  styles: `
    :host { display: block; }
    .summary {
      max-width: 76ch;
      color: var(--p-ink);
      font-size: var(--p-text-read);
      line-height: 1.5rem;
      letter-spacing: -0.009em;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .code, .plain {
      margin: 0;
      padding: 12px 14px;
      border: 1px solid var(--p-line);
      border-radius: var(--p-radius-control);
      background: var(--p-sunken);
      color: var(--p-ink);
      font-size: 12.5px;
      line-height: 1.25rem;
      letter-spacing: 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      tab-size: 2;
    }
    .plain { font-family: var(--p-font); font-size: var(--p-text-m); }
    .clamped { max-height: calc(1.25rem * 16); overflow: hidden; mask-image: linear-gradient(#000 70%, transparent); }
    .key { color: var(--p-accent-text); }
    .string { color: var(--p-ink); }
    .number, .literal { color: var(--p-ok-text); }
    .punct { color: var(--p-ink-2); }
    .actions { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; margin-left: -8px; }
  `,
})
export class ResultView {
  readonly text = input.required<string>();

  protected readonly expanded = signal(false);
  protected readonly showJson = signal(false);
  protected readonly copied = signal(false);

  protected readonly parsed = computed<Parsed>(() => parse(this.text()));
  protected readonly long = computed(() => {
    const view = this.parsed();
    const shown = view.summary !== null && !this.showJson() ? view.summary : view.json ? pretty(this.text()) : view.plain;
    return shown.split('\n').length > COLLAPSE_LINES || shown.length > 1400;
  });
  protected readonly clamped = computed(() => this.long() && !this.expanded());

  protected async copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(this.text());
      this.copied.set(true);
      setTimeout(() => this.copied.set(false), 1800);
    } catch {
      this.copied.set(false);
    }
  }
}

function parse(raw: string): Parsed {
  const text = raw.trim();
  const candidate = text.replace(/^```(?:json)?\s*/i, '').replace(/```$/, '').trim();
  if (candidate.startsWith('{') || candidate.startsWith('[')) {
    try {
      const value: unknown = JSON.parse(candidate);
      const summary =
        value && typeof value === 'object' && !Array.isArray(value) && typeof (value as {summary?: unknown}).summary === 'string'
          ? ((value as {summary: string}).summary)
          : null;
      return {summary, json: tokenize(JSON.stringify(value, null, 2)), plain: text};
    } catch {
      // Не JSON — покажем как текст
    }
  }
  return {summary: null, json: null, plain: text};
}

function pretty(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

function tokenize(json: string): Token[] {
  const tokens: Token[] = [];
  const pattern = /("(?:\\.|[^"\\])*")(\s*:)?|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|(true|false|null)|([{}[\],:])|(\s+)/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(json))) {
    if (match[1]) {
      tokens.push({kind: match[2] ? 'key' : 'string', text: match[1]});
      if (match[2]) tokens.push({kind: 'punct', text: match[2]});
    } else if (match[3]) tokens.push({kind: 'number', text: match[3]});
    else if (match[4]) tokens.push({kind: 'literal', text: match[4]});
    else if (match[5]) tokens.push({kind: 'punct', text: match[5]});
    else if (match[6]) tokens.push({kind: 'space', text: match[6]});
  }
  return tokens;
}
