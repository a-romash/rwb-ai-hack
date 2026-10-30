import {ChangeDetectionStrategy, Component, computed, input, output} from '@angular/core';
import {TuiButton, TuiIcon} from '@taiga-ui/core';
import {agentInfo} from '../../core/pipeline/agents.catalog';
import {phaseInfo, stageInfo} from '../../core/pipeline/stages.catalog';
import {jobStatusView} from '../../core/pipeline/status';
import {JobRecord} from '../../core/state/jobs.store';
import {clip} from '../../core/util/text';
import {formatDuration} from '../../core/util/time';
import {FlowStation} from '../../shared/ui/flow-map/flow.model';
import {RelTimePipe} from '../../shared/ui/rel-time.pipe';
import {StatusChip} from '../../shared/ui/status-chip';

/** Описание выбранной станции: смысл этапа, вход, выход, проверка, агент и последний запуск. */
@Component({
  selector: 'app-station-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiButton, TuiIcon, StatusChip, RelTimePipe],
  templateUrl: './station-panel.html',
  styleUrl: './station-panel.less',
})
export class StationPanel {
  readonly station = input.required<FlowStation>();
  readonly total = input(10);
  readonly job = input<JobRecord | null>(null);
  readonly now = input(Date.now());
  readonly run = output<string>();
  readonly openRuns = output<void>();

  protected readonly info = computed(() => stageInfo(this.station().key));
  protected readonly phase = computed(() => phaseInfo(this.station().phase));
  protected readonly agent = computed(() => agentInfo(this.info()?.agent));
  protected readonly jobView = computed(() => {
    const job = this.job();
    return job ? jobStatusView(job.status, job.subtype, job.stale) : null;
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
