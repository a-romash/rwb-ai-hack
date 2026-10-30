import {ChangeDetectionStrategy, Component, computed, inject, signal} from '@angular/core';
import {Router, RouterLink} from '@angular/router';
import {TuiIcon} from '@taiga-ui/core';
import {agentInfo} from '../../core/pipeline/agents.catalog';
import {AUTONOMY, stageInfo} from '../../core/pipeline/stages.catalog';
import {jobStatusView} from '../../core/pipeline/status';
import {Clock} from '../../core/state/clock.service';
import {JobRecord} from '../../core/state/jobs.store';
import {latestRun, PipelineGate, PipelineStage} from '../../shared/ui/pipeline/pipeline.model';
import {PipelineTimeline} from '../../shared/ui/pipeline/pipeline-timeline';
import {RelTimePipe} from '../../shared/ui/rel-time.pipe';
import {StatusChip} from '../../shared/ui/status-chip';
import {GatePanel} from './gate-panel';
import {RunLauncher} from './run-launcher';
import {StationPanel} from './station-panel';
import {WorkspaceStore} from './workspace.store';

/** Вкладка «Конвейер»: шаги Э1–Э7 с воротами качества и описание выбранной строки. */
@Component({
  selector: 'app-flow-tab',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, TuiIcon, PipelineTimeline, StationPanel, GatePanel, StatusChip, RelTimePipe],
  templateUrl: './flow-tab.html',
  styleUrl: './flow-tab.less',
})
export class FlowTab {
  protected readonly store = inject(WorkspaceStore);
  protected readonly clock = inject(Clock);
  private readonly launcher = inject(RunLauncher);
  private readonly router = inject(Router);

  private readonly picked = signal<string | null>(null);
  protected readonly autonomy = AUTONOMY.A2;

  /** Без явного выбора — первый шаг, который ещё не готов: туда и стоит идти. */
  protected readonly selectedId = computed(() => {
    const items = this.store.items();
    const picked = this.picked();
    if (picked && items.some(item => item.id === picked)) return picked;
    return (this.store.stages().find(stage => stage.tone !== 'ok') ?? this.store.stages()[0])?.id ?? null;
  });
  protected readonly selectedStage = computed<PipelineStage | null>(() => {
    const item = this.store.items().find(entry => entry.id === this.selectedId());
    return item?.kind === 'stage' ? item : null;
  });
  protected readonly selectedGate = computed<PipelineGate | null>(() => {
    const item = this.store.items().find(entry => entry.id === this.selectedId());
    return item?.kind === 'gate' ? item : null;
  });
  protected readonly selectedJob = computed<JobRecord | null>(() => {
    const stage = this.selectedStage();
    return stage ? latestRun(this.store.runs(), stage.key) : null;
  });
  protected readonly done = computed(() => this.store.stages().filter(stage => stage.tone === 'ok').length);
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

  protected select(id: string): void {
    this.picked.set(id);
  }

  protected run(stageKey: string): void {
    this.launcher.open(stageKey);
  }

  protected openRuns(): void {
    const id = this.store.id();
    if (id) void this.router.navigate(['/projects', id, 'runs']);
  }
}
