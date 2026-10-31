// Shape of generated/model.ts: ui.json screens plus the app.json parts the renderer reads.

export interface Widget {
  kind: string;
  testid: string;
  field?: string;
  query?: string;
  command?: string;
  agg?: string;
  label?: string;
  group?: string;
}

export interface Action {
  command: string;
  testid: string;
  confirm?: boolean;
  copy?: string;
  then?: string;
}

export interface Screen {
  platform: string;
  roles: string[];
  pattern: string;
  title: string;
  source?: {query?: string; entity?: string; command?: string; params?: string[]};
  widgets?: Widget[];
  filters?: {field: string; testid: string}[];
  actions?: Action[];
  live?: string[];
  states?: Record<string, string>;
  nav?: string[];
}

export interface FieldDef {
  type: string;
  label?: string;
  ref?: string;
  required?: boolean;
  nullable?: boolean;
  computed_by?: string;
  machine?: string;
}

export interface AppModel {
  platform: string;
  lang: string;
  title: string;
  device: string[];
  screens: Record<string, Screen>;
  menus: Record<string, string[]>;
  home: Record<string, string | null>;
  copy: Partial<Record<string, string>>;
  roles: Partial<Record<string, string>>;
  entities: Record<string, {label?: string; owner?: string; fields?: Record<string, FieldDef>}>;
  types: Record<string, {kind?: string; values?: string[]; labels?: Record<string, string>}>;
  queries: Record<string, {entity: string; filter?: string; order?: string}>;
  commands: Record<string, {entity: string; input?: Record<string, FieldDef>}>;
  machines: Record<string, {entity: string; states: string[]}>;
  seed_ids: Record<string, string[]>;
}

export type Row = Record<string, unknown> & {id?: string};
