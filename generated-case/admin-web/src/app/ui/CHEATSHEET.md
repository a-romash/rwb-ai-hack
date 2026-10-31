# UI facade cheat sheet

Compose these facades inside `src/app/custom/`. Do not add domain screens under `src/app/ui/`.

| Selector | Inputs | Notes |
| --- | --- | --- |
| `app-page` | `title` | Projects `[actions]` and the body |
| `app-data-table` | `columns`, `rows` | Cell text is `row[column]` |
| `app-filter-bar` | `query` | Emits `queryChange` |
| `app-status-chip` | `label` | Short status text |
| `app-map-view` | `lat`, `lng` | Grid and marker, no tile server |
| `app-timeline` | `events` | `at`, `title`, `detail` |
| `app-kpi-card` | `label`, `value` | One metric |
| `app-empty-state` | `title`, `message` | Shown when a list is empty |
| `app-confirm-dialog` | dialog data | Closes with `true` or `false` |
| `app-form-field` | `label`, `hint`, `value` | Emits `valueChange` |

Components are standalone, `OnPush`, and use signal inputs. Templates use `@if` and `@for`.

```html
<app-page title="Overview">
  <button actions type="button">Confirm</button>
  <app-filter-bar [query]="query()" (queryChange)="query.set($event)" />
  <app-data-table [columns]="columns" [rows]="rows()" />
  <app-empty-state title="No records" message="Nothing matches." />
</app-page>
```

Open the dialog with `MatDialog.open(AppConfirmDialog, { data: { title, message } })`.
Import the component class in the screen that renders it. There is no shared NgModule.
