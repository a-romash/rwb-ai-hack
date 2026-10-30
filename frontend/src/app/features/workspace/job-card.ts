import {ChangeDetectionStrategy, Component, computed, input, output} from '@angular/core';
import {TuiButton, TuiHint, TuiIcon} from '@taiga-ui/core';
import {agentInfo} from '../../core/pipeline/agents.catalog';
import {stageInfo} from '../../core/pipeline/stages.catalog';
import {jobStatusView} from '../../core/pipeline/status';
import {JobRecord} from '../../core/state/jobs.store';
import {formatNumber, plural} from '../../core/util/text';
import {formatDuration, fullDate} from '../../core/util/time';
import {RelTimePipe} from '../../shared/ui/rel-time.pipe';
import {ResultView} from '../../shared/ui/result-view';
import {StatusChip} from '../../shared/ui/status-chip';

/** Запуск агента: статус, длительность, результат и инструкция, с которой он запускался. */
@Component({
  selector: 'app-job-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiButton, TuiIcon, TuiHint, StatusChip, ResultView, RelTimePipe],
  templateUrl: './job-card.html',
  styleUrl: './job-card.less',
  host: {'[attr.data-tone]': 'view().tone'},
})
export class JobCard {
  readonly job = input.required<JobRecord>();
  readonly now = input(Date.now());
  readonly refresh = output<string>();
  readonly remove = output<string>();

  protected readonly view = computed(() => {
    const job = this.job();
    return jobStatusView(job.status, job.subtype, job.stale);
  });
  protected readonly agent = computed(() => agentInfo(this.job().agent));
  protected readonly stage = computed(() => stageInfo(this.job().stageKey));
  protected readonly fullDate = fullDate;

  protected readonly duration = computed(() => {
    const job = this.job();
    if (job.durationMs) return formatDuration(job.durationMs);
    const end = job.finishedAt ?? (this.view().terminal ? job.updatedAt : this.now());
    return formatDuration(end - job.createdAt);
  });

  protected readonly facts = computed(() => {
    const job = this.job();
    const facts: {label: string; value: string}[] = [];
    if (job.numTurns != null) facts.push({label: 'Шагов', value: `${job.numTurns}`});
    const usage = job.usage;
    if (usage?.total_tokens != null) facts.push({label: 'Токенов', value: formatNumber(usage.total_tokens)});
    if (usage?.reasoning_tokens) facts.push({label: 'Из них рассуждения', value: formatNumber(usage.reasoning_tokens)});
    if (usage?.attempts != null) facts.push({label: 'Попыток', value: `${usage.attempts}`});
    return facts;
  });

  protected readonly promptLabel = computed(() => {
    const job = this.job();
    if (!job.promptLength) return 'Требования проекта без инструкции';
    return `Инструкция и требования: ${formatNumber(job.promptLength)} ${plural(job.promptLength, ['символ', 'символа', 'символов'])}`;
  });

  protected readonly canRefresh = computed(() => {
    const job = this.job();
    return !this.view().terminal || job.stale || Boolean(job.lastError) || job.expired;
  });
}
