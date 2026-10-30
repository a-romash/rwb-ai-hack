import {ChangeDetectionStrategy, Component, computed, inject, signal} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDialog} from '@angular/material/dialog';
import {AppConfirmDialog} from './ui/confirm-dialog';
import {AppDataTable} from './ui/data-table';
import {AppEmptyState} from './ui/empty-state';
import {AppFilterBar} from './ui/filter-bar';
import {AppFormField} from './ui/form-field';
import {AppKpiCard} from './ui/kpi-card';
import {AppMapView} from './ui/map-view';
import {AppPage} from './ui/page';
import {AppStatusChip} from './ui/status-chip';
import {AppTimeline, TimelineEvent} from './ui/timeline';

@Component({
  selector: 'app-home',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    MatButtonModule,
    AppPage,
    AppStatusChip,
    AppKpiCard,
    AppFilterBar,
    AppDataTable,
    AppEmptyState,
    AppMapView,
    AppTimeline,
    AppFormField,
  ],
  template: `
    <app-page title="Overview">
      <button actions mat-stroked-button type="button" (click)="confirm()">Confirm</button>
      <app-status-chip label="Ready" />
      <div class="kpis">
        @for (item of kpis(); track item.label) {
          <app-kpi-card [label]="item.label" [value]="item.value" />
        }
      </div>
      <app-filter-bar [query]="query()" (queryChange)="query.set($event)" />
      @if (filtered().length === 0) {
        <app-empty-state title="No records" message="Nothing matches this filter." />
      } @else {
        <app-data-table [columns]="columns" [rows]="filtered()" />
      }
      <app-map-view [lat]="0" [lng]="0" />
      <app-timeline [events]="events" />
      <app-form-field label="Note" hint="Optional" [value]="note()" (valueChange)="note.set($event)" />
    </app-page>
  `,
  styles: `
    .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
  `,
})
export class Home {
  private readonly dialog = inject(MatDialog);
  private readonly records: Record<string, string>[] = [
    {name: 'Alpha', state: 'Active'},
    {name: 'Beta', state: 'Idle'},
  ];

  readonly columns = ['name', 'state'];
  readonly events: readonly TimelineEvent[] = [
    {at: '08:00', title: 'Created', detail: 'Record opened'},
    {at: '09:30', title: 'Updated', detail: 'State changed'},
  ];
  readonly query = signal('');
  readonly note = signal('');
  readonly filtered = computed(() => {
    const query = this.query().trim().toLowerCase();
    if (!query) {
      return this.records;
    }
    return this.records.filter((row) =>
      Object.values(row).some((value) => value.toLowerCase().includes(query)),
    );
  });
  readonly kpis = computed(() => [
    {label: 'Records', value: String(this.records.length)},
    {label: 'Active', value: String(this.records.filter((row) => row['state'] === 'Active').length)},
  ]);

  confirm(): void {
    this.dialog.open(AppConfirmDialog, {
      data: {title: 'Confirm', message: 'Continue with this action?'},
    });
  }
}
