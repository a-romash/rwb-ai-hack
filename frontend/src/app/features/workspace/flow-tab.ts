import {ChangeDetectionStrategy, Component, computed, inject, signal} from '@angular/core';
import {Router, RouterLink} from '@angular/router';
import {TuiIcon} from '@taiga-ui/core';
import {agentInfo} from '../../core/pipeline/agents.catalog';
import {stageInfo} from '../../core/pipeline/stages.catalog';
import {jobStatusView} from '../../core/pipeline/status';
import {Clock} from '../../core/state/clock.service';
import {JobRecord} from '../../core/state/jobs.store';
import {FlowMap} from '../../shared/ui/flow-map/flow-map';
import {RelTimePipe} from '../../shared/ui/rel-time.pipe';
import {StatusChip} from '../../shared/ui/status-chip';
import {RunLauncher} from './run-launcher';
import {StationPanel} from './station-panel';
import {WorkspaceStore} from './workspace.store';

/** Вкладка «Поток»: линия этапов и описание выбранной станции. */
@Component({
  selector: 'app-flow-tab',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, TuiIcon, FlowMap, StationPanel, StatusChip, RelTimePipe],
  templateUrl: './flow-tab.html',
  styleUrl: './flow-tab.less',
})
export class FlowTab {
  protected readonly store = inject(WorkspaceStore);
  protected readonly clock = inject(Clock);
  private readonly launcher = inject(RunLauncher);
  private readonly router = inject(Router);

  private readonly picked = signal<string | null>(null);

  /** Без явного выбора — первая станция, которая ещё не готова: туда и стоит идти. */
  protected readonly selectedKey = computed(() => {
    const stations = this.store.stations();
    const picked = this.picked();
    if (picked && stations.some(station => station.key === picked)) return picked;
    return (stations.find(station => station.tone !== 'ok') ?? stations[0])?.key ?? null;
  });
  protected readonly selected = computed(() => this.store.stations().find(station => station.key === this.selectedKey()) ?? null);
  protected readonly selectedJob = computed<JobRecord | null>(() => {
    const key = this.selectedKey();
    return key ? this.store.latestByStage().get(key) ?? null : null;
  });
  protected readonly recent = computed(() =>
    this.store
      .runs()
      .slice(0, 4)
      .map(run => ({
        run,
        view: jobStatusView(run.status, run.subtype, run.stale),
        agent: agentInfo(run.agent),
        stage: stageInfo(run.stageKey),
      })),
  );

  protected select(key: string): void {
    this.picked.set(key);
  }

  protected run(stageKey: string): void {
    this.launcher.open(stageKey);
  }

  protected openRuns(): void {
    const id = this.store.id();
    if (id) void this.router.navigate(['/projects', id, 'runs']);
  }
}
