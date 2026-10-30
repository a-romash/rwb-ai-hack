import {ChangeDetectionStrategy, Component, computed, input, output} from '@angular/core';
import {TuiButton, TuiIcon} from '@taiga-ui/core';
import {agentInfo} from '../../core/pipeline/agents.catalog';
import {GATES, PARTICIPANTS} from '../../core/pipeline/stages.catalog';
import {jobStatusView} from '../../core/pipeline/status';
import {JobRecord} from '../../core/state/jobs.store';
import {clip} from '../../core/util/text';
import {formatDuration} from '../../core/util/time';
import {stageStatusView} from '../../core/pipeline/status';
import {PipelineStage} from '../../shared/ui/pipeline/pipeline.model';
import {RelTimePipe} from '../../shared/ui/rel-time.pipe';
import {StatusChip} from '../../shared/ui/status-chip';

/** Описание шага конвейера: смысл, вход, выход, ворота, участники, агент и последний запуск. */
@Component({
  selector: 'app-station-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiButton, TuiIcon, StatusChip, RelTimePipe],
  templateUrl: './station-panel.html',
  styleUrl: './station-panel.less',
})
export class StationPanel {
  readonly stage = input.required<PipelineStage>();
  readonly total = input(8);
  readonly job = input<JobRecord | null>(null);
  readonly now = input(Date.now());
  readonly run = output<string>();
  readonly openRuns = output<void>();
  readonly openGate = output<string>();
  readonly retry = output<string>();

  protected readonly info = computed(() => this.stage().info);
  protected readonly gates = computed(() => this.info().gates.map(key => GATES[key]));
  protected readonly participants = computed(() => this.info().participants.map(key => PARTICIPANTS[key] ?? key));
  protected readonly agent = computed(() => agentInfo(this.info().agent));
  protected readonly jobView = computed(() => {
    const job = this.job();
    return job ? jobStatusView(job.status, job.subtype, job.stale) : null;
  });
  protected readonly stageRun = computed(() => this.stage().stageRun ?? null);
  protected readonly stageRunView = computed(() => {
    const run = this.stageRun();
    return run ? stageStatusView(run.status) : null;
  });
  protected readonly stageElapsed = computed(() => {
    const run = this.stageRun();
    if (!run?.started_at) return '';
    const end = run.finished_at ? Date.parse(run.finished_at) : this.now();
    return formatDuration(end - Date.parse(run.started_at));
  });
  protected readonly elapsed = computed(() => {
    const job = this.job();
    if (!job) return '';
    const end = job.finishedAt ?? this.now();
    return formatDuration(end - job.createdAt);
  });
  protected readonly excerpt = computed(() => {
    const result = this.job()?.result;
    if (!result) return null;
    try {
      const parsed: unknown = JSON.parse(result);
      if (parsed && typeof parsed === 'object' && typeof (parsed as {summary?: unknown}).summary === 'string') {
        return clip((parsed as {summary: string}).summary, 320);
      }
    } catch {
      // текстовый результат
    }
    return clip(result, 320);
  });
}
