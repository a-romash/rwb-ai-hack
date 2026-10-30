import {DIALOG_DATA, DialogRef} from '@angular/cdk/dialog';
import {ChangeDetectionStrategy, Component, computed, inject, signal} from '@angular/core';
import {Router} from '@angular/router';
import {TuiButton, TuiIcon} from '@taiga-ui/core';
import {TuiSegmented} from '@taiga-ui/kit';
import {readableError, ReadableError} from '../../core/api/errors';
import {AGENT_LIST, AgentId, AGENTS} from '../../core/pipeline/agents.catalog';
import {stageInfo} from '../../core/pipeline/stages.catalog';
import {ToastService} from '../../core/state/toast.service';
import {estimateTokens, formatNumber} from '../../core/util/text';
import {WorkspaceStore} from './workspace.store';

export interface RunDialogData {
  stageKey: string | null;
  agent: string | null;
}

const PROMPT_MAX = 50_000;

/**
 * Запуск агента. Инструкция этапа редактируется, требования проекта добавляются к ней целиком.
 * Без инструкции бэкенд сам передаст агенту требования проекта.
 */
@Component({
  selector: 'app-run-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiButton, TuiIcon, TuiSegmented],
  host: {class: 'dialog-surface', '(keydown)': 'onKeydown($event)'},
  templateUrl: './run-dialog.html',
  styleUrl: './run-dialog.less',
})
export class RunDialog {
  private readonly data = inject<RunDialogData>(DIALOG_DATA);
  private readonly ref = inject(DialogRef);
  private readonly store = inject(WorkspaceStore);
  private readonly toasts = inject(ToastService);
  private readonly router = inject(Router);

  protected readonly agents = AGENT_LIST;
  protected readonly stage = stageInfo(this.data.stageKey);
  protected readonly isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);

  protected readonly agentIndex = signal(
    Math.max(0, AGENT_LIST.findIndex(agent => agent.id === (this.data.agent ?? this.stage?.agent ?? 'analyst'))),
  );
  protected readonly agent = computed(() => AGENT_LIST[this.agentIndex()]);
  protected readonly instruction = signal(this.stage?.preset ?? '');
  protected readonly sending = signal(false);
  protected readonly error = signal<ReadableError | null>(null);

  private readonly requirements = computed(() => this.store.project()?.requirements ?? '');
  protected readonly prompt = computed(() => {
    const instruction = this.instruction().trim();
    return instruction ? `${instruction}\n\nТребования проекта:\n${this.requirements()}` : null;
  });
  protected readonly size = computed(() => {
    const text = this.prompt() ?? this.requirements();
    return {chars: text.length, label: formatNumber(text.length), tokens: formatNumber(estimateTokens(text))};
  });
  protected readonly tooLong = computed(() => this.size().chars > PROMPT_MAX);
  protected readonly requirementsSize = computed(() => formatNumber(this.requirements().length));
  protected readonly presetChanged = computed(() => (this.stage?.preset ?? '') !== this.instruction());

  protected resetInstruction(): void {
    this.instruction.set(this.stage?.preset ?? '');
  }

  protected onInstruction(event: Event): void {
    this.instruction.set((event.target as HTMLTextAreaElement).value);
  }

  protected start(): void {
    if (this.sending() || this.tooLong()) return;
    const agent: AgentId = this.agent().id;
    this.sending.set(true);
    this.error.set(null);
    this.store.start({agent, prompt: this.prompt(), stageKey: this.stage?.key ?? null}).subscribe({
      next: () => {
        this.ref.close(true);
        const id = this.store.id();
        const onRuns = this.router.url.endsWith('/runs');
        this.toasts.info(
          `${AGENTS[agent].name} запущен`,
          'Задача в очереди. Статус обновляется сам.',
          onRuns || !id ? undefined : {label: 'Открыть запуски', run: () => void this.router.navigate(['/projects', id, 'runs'])},
        );
      },
      error: error => {
        this.sending.set(false);
        this.error.set(readableError(error, 'job'));
      },
    });
  }

  protected close(): void {
    this.ref.close(false);
  }

  protected onKeydown(event: KeyboardEvent): void {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      this.start();
    }
  }
}
