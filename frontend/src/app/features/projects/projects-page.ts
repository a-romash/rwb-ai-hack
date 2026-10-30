import {ChangeDetectionStrategy, Component, computed, inject, signal} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {RouterLink} from '@angular/router';
import {TuiButton, TuiIcon, TuiInput} from '@taiga-ui/core';
import {TuiSegmented, TuiSkeleton} from '@taiga-ui/kit';
import {ProjectSummary} from '../../core/api/api.types';
import {STAGE_CATALOG} from '../../core/pipeline/stages.catalog';
import {jobStatusView, StatusView} from '../../core/pipeline/status';
import {Clock} from '../../core/state/clock.service';
import {JobsStore} from '../../core/state/jobs.store';
import {ProjectsStore} from '../../core/state/projects.store';
import {ShellService} from '../../core/state/shell.service';
import {plural} from '../../core/util/text';
import {fullDate} from '../../core/util/time';
import {PipelineChain} from '../../shared/ui/pipeline/pipeline-chain';
import {PipelineMini} from '../../shared/ui/pipeline/pipeline-mini';
import {buildPipeline, PipelineStage} from '../../shared/ui/pipeline/pipeline.model';
import {RelTimePipe} from '../../shared/ui/rel-time.pipe';
import {StatusChip} from '../../shared/ui/status-chip';

interface Row {
  project: ProjectSummary;
  stages: PipelineStage[];
  status: StatusView;
  done: number;
}

@Component({
  selector: 'app-projects-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    FormsModule,
    TuiButton,
    TuiIcon,
    TuiInput,
    TuiSegmented,
    TuiSkeleton,
    PipelineChain,
    PipelineMini,
    StatusChip,
    RelTimePipe,
  ],
  templateUrl: './projects-page.html',
  styleUrl: './projects-page.less',
})
export class ProjectsPage {
  protected readonly store = inject(ProjectsStore);
  protected readonly clock = inject(Clock);
  private readonly jobs = inject(JobsStore);

  protected readonly query = signal('');
  protected readonly sort = signal(0);
  protected readonly fullDate = fullDate;

  protected readonly rows = computed<Row[]>(() => {
    const words = this.query().toLowerCase().trim();
    const list = this.store.items().filter(project => !words || project.name.toLowerCase().includes(words));
    const sorted = this.sort() === 1 ? [...list].sort((a, b) => a.name.localeCompare(b.name, 'ru')) : list;
    return sorted.map(project => this.row(project));
  });

  protected readonly countLabel = computed(() => {
    const count = this.store.items().length;
    return `${count} ${plural(count, ['проект', 'проекта', 'проектов'])}`;
  });

  constructor() {
    const shell = inject(ShellService);
    shell.crumbs.set([{label: 'Проекты'}]);
    shell.projectId.set(null);
    this.store.load();
  }

  private row(project: ProjectSummary): Row {
    const runs = this.jobs.list(project.id);
    const stages = buildPipeline(runs);
    const live = runs.find(run => jobStatusView(run.status, run.subtype, run.stale).live);
    const last = runs[0];
    const status: StatusView = live
      ? {tone: 'run', label: 'Агент работает', live: true}
      : last
        ? jobStatusView(last.status, last.subtype, last.stale)
        : {tone: 'idle', label: 'Не запускался', live: false};
    return {project, stages, status, done: stages.filter(stage => stage.tone === 'ok').length};
  }

  protected readonly stageCount = STAGE_CATALOG.length;
}
