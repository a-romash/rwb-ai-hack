import {ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDialog} from '@angular/material/dialog';
import {ActivatedRoute, Router, RouterLink} from '@angular/router';
import {firstValueFrom} from 'rxjs';
import {MODEL} from '../generated/model';
import {AppConfirmDialog} from '../ui/confirm-dialog';
import {AppEmptyState} from '../ui/empty-state';
import {AppKpiCard} from '../ui/kpi-card';
import {AppPage} from '../ui/page';
import {Action, Row, Screen, Widget} from './model';
import {currentUser, display, enumValues, fieldDef, fieldLabel, matches, ordered} from './query';
import {ApiError, Session} from './session';

type View = 'loading' | 'ready' | 'empty' | 'error' | 'forbidden' | 'offline';

const COLLECTIONS = new Set(['list', 'feed', 'kanban', 'calendar', 'map']);
const FORMS = new Set(['form', 'wizard', 'action', 'settings']);

/** Renders any ui.json screen: the product has no hand-written screens, only this and the model. */
@Component({
  selector: 'app-screen-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatButtonModule, RouterLink, AppPage, AppEmptyState, AppKpiCard],
  templateUrl: './screen-page.html',
  styleUrl: './screen-page.css',
})
export class ScreenPage {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly dialog = inject(MatDialog);
  private readonly session = inject(Session);

  readonly model = MODEL;
  readonly name: string = this.route.snapshot.data['screen'];
  readonly screen: Screen = MODEL.screens[this.name];
  readonly kebab = kebab(this.name);
  readonly id = signal<string | null>(this.route.snapshot.queryParamMap.get('id'));
  readonly entity = entityOf(this.screen);
  readonly kind = COLLECTIONS.has(this.screen.pattern)
    ? 'collection'
    : FORMS.has(this.screen.pattern)
      ? 'form'
      : this.screen.pattern === 'dashboard'
        ? 'dashboard'
        : 'detail';

  readonly view = signal<View>('loading');
  readonly rows = signal<Row[]>([]);
  readonly item = signal<Row | null>(null);
  readonly kpis = signal<Partial<Record<string, string>>>({});
  readonly values = signal<Partial<Record<string, string | boolean>>>({});
  readonly filterValues = signal<Record<string, string>>({});
  readonly failure = signal<string | null>(null);
  readonly busy = signal(false);
  readonly now = signal(Date.now());

  readonly fields = (this.screen.widgets ?? []).filter((w) => w.kind !== 'kpi' && w.kind !== 'action_button');
  readonly buttons = (this.screen.widgets ?? []).filter((w) => w.kind === 'action_button');
  readonly rowActions = (this.screen.actions ?? []).filter((a) => !a.command.includes('.'));
  readonly nav = (this.screen.nav ?? []).filter((name) => MODEL.screens[name]);
  readonly groups = computed(() => {
    const groups = new Map<string, Widget[]>();
    for (const widget of this.fields) {
      const key = widget.group ? (MODEL.copy[widget.group] ?? '') : '';
      groups.set(key, [...(groups.get(key) ?? []), widget]);
    }
    return [...groups].map(([title, widgets]) => ({title, widgets}));
  });
  readonly visibleRows = computed(() => {
    const filters = Object.entries(this.filterValues()).filter(([, value]) => value);
    return this.rows().filter((row) =>
      filters.every(([path, value]) => String(row[path.split('.')[1]] ?? '') === value),
    );
  });

  constructor() {
    const timers = [setInterval(() => this.now.set(Date.now()), 30_000)];
    // shortcut: live events refresh by polling; switch to the product SSE stream once events are generated.
    if (this.screen.live?.length && this.kind !== 'form') {
      timers.push(setInterval(() => void this.load(false), 15_000));
    }
    inject(DestroyRef).onDestroy(() => timers.forEach(clearInterval));
    void this.load(true);
  }

  state(key: string): string {
    return this.screen.states?.[key] ?? '';
  }

  label(widget: Widget): string {
    return widget.label ? (MODEL.copy[widget.label] ?? widget.label) : fieldLabel(MODEL, widget.field ?? '');
  }

  text(widget: Widget, row: Row | null): string {
    const def = fieldDef(MODEL, widget.field ?? '');
    const value = row?.[(widget.field ?? '').split('.')[1]];
    if (widget.kind === 'countdown') {
      return countdown(value, this.now(), MODEL.lang);
    }
    return display(MODEL, def, value, MODEL.lang);
  }

  overdue(widget: Widget, row: Row | null): boolean {
    const value = row?.[(widget.field ?? '').split('.')[1]];
    return widget.kind === 'countdown' && typeof value === 'string' && Date.parse(value) < this.now();
  }

  input(widget: Widget): {type: string; options: string[]} {
    const def = fieldDef(MODEL, widget.field ?? '');
    const options = enumValues(MODEL, def);
    if (options.length) return {type: 'choice', options};
    const type = def?.type ?? 'string';
    const html: Record<string, string> = {
      text: 'textarea', bool: 'checkbox', datetime: 'datetime-local', date: 'date',
      int: 'number', decimal: 'number', money: 'number', number: 'number', file: 'file',
    };
    return {type: html[type] ?? 'text', options};
  }

  setValue(widget: Widget, value: string | boolean): void {
    this.values.update((values) => ({...values, [widget.field!.split('.')[1]]: value}));
  }

  setFilter(path: string, value: string): void {
    this.filterValues.update((values) => ({...values, [path]: value}));
  }

  filterOptions(path: string): string[] {
    return enumValues(MODEL, fieldDef(MODEL, path));
  }

  open(row: Row): void {
    const detail = this.nav.find((name) => MODEL.screens[name].pattern === 'detail');
    if (detail && row.id) {
      void this.router.navigate(['/' + detail], {queryParams: {id: row.id}});
    }
  }

  canLocate(widget: Widget): boolean {
    return MODEL.device.includes('location') && /^(geo|point|location|geometry)$/.test(fieldDef(MODEL, widget.field ?? '')?.type ?? '');
  }

  locate(widget: Widget): void {
    navigator.geolocation?.getCurrentPosition(
      (position) => this.setValue(widget, `POINT(${position.coords.longitude} ${position.coords.latitude})`),
      () => this.failure.set('Нет доступа к геолокации'),
    );
  }

  async run(action: Action, row: Row | null): Promise<void> {
    if (action.confirm) {
      const text = action.copy ? (MODEL.copy[action.copy] ?? '') : '';
      const ok = await firstValueFrom(
        this.dialog
          .open(AppConfirmDialog, {data: {title: this.screen.title, message: text, confirm: 'Да', cancel: 'Отмена'}})
          .afterClosed(),
      );
      if (!ok) return;
    }
    this.busy.set(true);
    this.failure.set(null);
    try {
      const result = await this.send(action, row);
      if (action.then) {
        const id = result?.id ?? row?.id ?? this.id();
        await this.router.navigate(['/' + action.then], {queryParams: id ? {id} : {}});
      } else {
        await this.load(false);
      }
    } catch (error) {
      this.failure.set(error instanceof ApiError ? error.message : 'Не удалось выполнить действие');
    } finally {
      this.busy.set(false);
    }
  }

  private send(action: Action, row: Row | null): Promise<Row | undefined> {
    const [owner, verb] = action.command.split('.');
    const values = this.payload();
    const id = row?.id ?? this.id();
    if (verb === 'create') return this.session.request('POST', `/${owner}`, {...defaults(owner), ...values});
    if (verb === 'update') return this.session.request('PUT', `/${owner}/${id}`, {...this.item(), ...values});
    if (verb === 'delete') return this.session.request('DELETE', `/${owner}/${id}`);
    const entity = MODEL.commands[owner]?.entity ?? this.entity;
    return this.session.request('POST', `/${entity}/commands/${owner}`, {...values, id});
  }

  private payload(): Record<string, unknown> {
    const result: Record<string, unknown> = {};
    for (const widget of this.fields) {
      const name = (widget.field ?? '').split('.')[1];
      const value = this.values()[name];
      if (value === undefined || value === '') continue;
      const type = fieldDef(MODEL, widget.field ?? '')?.type;
      result[name] =
        type && ['int', 'decimal', 'money', 'number'].includes(type)
          ? Number(value)
          : type === 'datetime' && typeof value === 'string'
            ? new Date(value).toISOString()
            : value;
    }
    return result;
  }

  async load(first: boolean): Promise<void> {
    if (!navigator.onLine) {
      this.view.set('offline');
      return;
    }
    if (first) this.view.set('loading');
    try {
      if (this.kind === 'collection') {
        const query = MODEL.queries[this.screen.source?.query ?? ''];
        const rows = await this.session.request<Row[]>('GET', `/${this.entity}`);
        const user = currentUser(MODEL, this.entity, query?.filter);
        const next = ordered(rows.filter((row) => matches(row, query?.filter, user)), query?.order);
        notifyNew(this.screen.title, this.rows(), next, first);
        this.rows.set(next);
        this.view.set(next.length ? 'ready' : 'empty');
      } else if (this.kind === 'dashboard') {
        this.kpis.set(await this.aggregates());
        this.view.set('ready');
      } else if (this.id() && this.entity) {
        const item = await this.session.request<Row>('GET', `/${this.entity}/${this.id()}`);
        this.item.set(item);
        if (first && this.kind === 'form' && this.screen.source?.entity) {
          this.values.set(Object.fromEntries(Object.entries(item).map(([k, v]) => [k, v as string])));
        }
        this.view.set('ready');
      } else {
        this.view.set(this.kind === 'form' ? 'ready' : 'empty');
      }
    } catch (error) {
      this.view.set(error instanceof ApiError && (error.status === 401 || error.status === 403) ? 'forbidden' : 'error');
    }
  }

  private async aggregates(): Promise<Record<string, string>> {
    const result: Record<string, string> = {};
    const cache = new Map<string, Promise<Row[]>>();
    for (const widget of (this.screen.widgets ?? []).filter((w) => w.kind === 'kpi')) {
      const query = MODEL.queries[widget.query ?? ''];
      const entity = query?.entity ?? widget.field?.split('.')[0] ?? '';
      if (!cache.has(entity)) cache.set(entity, this.session.request<Row[]>('GET', `/${entity}`));
      const rows = (await cache.get(entity)!).filter((row) =>
        matches(row, query?.filter, currentUser(MODEL, entity, query?.filter)),
      );
      const numbers = rows.map((row) => Number(row[(widget.field ?? '').split('.')[1]])).filter(Number.isFinite);
      const agg = widget.agg ?? 'count';
      const value =
        agg === 'count' ? rows.length
          : !numbers.length ? null
          : agg === 'sum' ? numbers.reduce((a, b) => a + b, 0)
          : agg === 'avg' ? numbers.reduce((a, b) => a + b, 0) / numbers.length
          : agg === 'min' ? Math.min(...numbers)
          : Math.max(...numbers);
      result[widget.testid] = value === null ? '—' : new Intl.NumberFormat(MODEL.lang, {maximumFractionDigits: 1}).format(value);
    }
    return result;
  }
}

export function kebab(name: string): string {
  return name.replace(/(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])/g, '-').toLowerCase();
}

function entityOf(screen: Screen): string {
  const source = screen.source ?? {};
  if (source.query) return MODEL.queries[source.query]?.entity ?? '';
  if (source.command) return MODEL.commands[source.command]?.entity ?? '';
  return source.entity ?? '';
}

/**
 * Required fields the form does not ask for. shortcut: a reference points at the first seeded row
 * (sign-in is by role, there is no user record); timestamps are now. Server-side defaults replace this.
 */
function defaults(entity: string): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [name, def] of Object.entries(MODEL.entities[entity]?.fields ?? {})) {
    if (!def.required || def.computed_by) continue;
    if (def.type === 'datetime') result[name] = new Date().toISOString();
    else if (def.type === 'ref' && MODEL.seed_ids[def.ref ?? '']?.length) result[name] = MODEL.seed_ids[def.ref!][0];
    else if (def.type === 'bool') result[name] = false;
  }
  return result;
}

function countdown(value: unknown, now: number, lang: string): string {
  if (typeof value !== 'string') return '—';
  const minutes = Math.round((Date.parse(value) - now) / 60_000);
  const format = new Intl.RelativeTimeFormat(lang, {numeric: 'auto'});
  return Math.abs(minutes) < 90 ? format.format(minutes, 'minute') : format.format(Math.round(minutes / 60), 'hour');
}

/** A local notification when a live list gains rows (PWA with local_notification). */
function notifyNew(title: string, before: Row[], after: Row[], first: boolean): void {
  if (first || !MODEL.device.includes('local_notification') || typeof Notification === 'undefined') return;
  const known = new Set(before.map((row) => row.id));
  const added = after.filter((row) => !known.has(row.id)).length;
  if (added && Notification.permission === 'granted') {
    new Notification(title, {body: `Новых записей: ${added}`});
  }
}
