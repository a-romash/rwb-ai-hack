import {AppModel, FieldDef, Row} from './model';

const CLAUSE = /^\s*([a-z][a-z0-9_]*)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*$/;

/**
 * Client-side filter for app.json queries: `a == b and c != null or d == current_user`.
 * shortcut: the stand has no query endpoints yet, so lists read /api/<Entity> and filter here;
 * move the filter server-side when queries are generated. An expression this grammar cannot
 * read keeps every row instead of hiding data.
 */
export function matches(row: Row, filter: string | undefined, currentUser: string | null): boolean {
  if (!filter?.trim()) {
    return true;
  }
  return filter.split(/\s+or\s+/).some((part) =>
    part.split(/\s+and\s+/).every((clause) => {
      const match = CLAUSE.exec(clause);
      if (!match) {
        return true;
      }
      const [, field, op, raw] = match;
      const actual = row[field] ?? null;
      const expected = literal(raw, currentUser);
      if (op === '==') return actual === expected || String(actual) === String(expected);
      if (op === '!=') return !(actual === expected || String(actual) === String(expected));
      if (actual === null || expected === null) return false;
      const [a, b] = [String(actual), String(expected)];
      return op === '>' ? a > b : op === '<' ? a < b : op === '>=' ? a >= b : a <= b;
    }),
  );
}

function literal(raw: string, currentUser: string | null): unknown {
  if (raw === 'null') return null;
  if (raw === 'true' || raw === 'false') return raw === 'true';
  if (raw === 'current_user') return currentUser;
  if (/^-?\d+(\.\d+)?$/.test(raw)) return Number(raw);
  return raw.replace(/^['"]|['"]$/g, '');
}

export function ordered(rows: Row[], order: string | undefined): Row[] {
  if (!order) {
    return rows;
  }
  const field = order.replace(/^-/, '');
  const sign = order.startsWith('-') ? -1 : 1;
  return [...rows].sort((a, b) => sign * String(a[field] ?? '').localeCompare(String(b[field] ?? '')));
}

/** Entity.field or Command.input -> definition from app.json. */
export function fieldDef(model: AppModel, path: string): FieldDef | undefined {
  const [owner, name] = path.split('.');
  return model.entities[owner]?.fields?.[name] ?? model.commands[owner]?.input?.[name];
}

export function fieldLabel(model: AppModel, path: string): string {
  return fieldDef(model, path)?.label ?? path.split('.')[1];
}

export function enumValues(model: AppModel, def: FieldDef | undefined): string[] {
  if (!def) return [];
  if (def.type === 'state') return model.machines[def.machine ?? '']?.states ?? [];
  return def.ref ? (model.types[def.ref]?.values ?? []) : [];
}

export function display(model: AppModel, def: FieldDef | undefined, value: unknown, lang: string): string {
  if (value === null || value === undefined || value === '') return '—';
  if (def?.type === 'datetime' && typeof value === 'string') {
    return new Date(value).toLocaleString(lang, {dateStyle: 'short', timeStyle: 'short'});
  }
  if (def?.type === 'bool') return value ? 'Да' : 'Нет';
  if (def?.ref && model.types[def.ref]?.labels) return model.types[def.ref].labels![String(value)] ?? String(value);
  return String(value);
}

/**
 * Who `current_user` is. shortcut: sign-in is by role, so a person is the first seeded row of the
 * referenced entity (Employee[0]); replace with the user id claim once the stand has real accounts.
 */
export function currentUser(model: AppModel, entity: string, filter: string | undefined): string | null {
  const field = /([a-z][a-z0-9_]*)\s*==\s*current_user/.exec(filter ?? '')?.[1];
  const ref = field ? model.entities[entity]?.fields?.[field]?.ref : undefined;
  return (ref && model.seed_ids[ref]?.[0]) ?? null;
}
