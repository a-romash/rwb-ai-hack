import {DialogRef} from '@angular/cdk/dialog';
import {ChangeDetectionStrategy, Component, computed, ElementRef, inject, signal, viewChild} from '@angular/core';
import {Router} from '@angular/router';
import {TuiIcon} from '@taiga-ui/core';
import {ProjectsStore} from '../../core/state/projects.store';
import {ShellService} from '../../core/state/shell.service';
import {ThemeService} from '../../core/state/theme.service';

interface Command {
  id: string;
  group: string;
  label: string;
  hint?: string;
  icon: string;
  keywords: string;
  run: () => void;
}

/** Командная палитра: переход к проекту или разделу и частые действия без мыши. */
@Component({
  selector: 'app-command-palette',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiIcon],
  host: {class: 'dialog-surface'},
  templateUrl: './command-palette.html',
  styleUrl: './command-palette.less',
})
export class CommandPalette {
  private readonly ref = inject(DialogRef);
  private readonly router = inject(Router);
  private readonly projects = inject(ProjectsStore);
  private readonly shell = inject(ShellService);
  private readonly theme = inject(ThemeService);
  private readonly list = viewChild<ElementRef<HTMLElement>>('list');

  protected readonly query = signal('');
  protected readonly active = signal(0);

  private readonly commands = computed<Command[]>(() => {
    const commands: Command[] = [];
    const current = this.shell.projectId();
    if (current) {
      const name = this.projects.items().find(project => project.id === current)?.name ?? 'Проект';
      commands.push(
        {id: 'tab-flow', group: name, label: 'Конвейер', hint: 'Шаги Э1–Э7 и ворота', icon: '@tui.workflow', keywords: 'конвейер поток этапы шаги ворота', run: () => this.go(['/projects', current, 'flow'])},
        {id: 'tab-req', group: name, label: 'Требования', hint: 'Текст и полнота', icon: '@tui.file-text', keywords: 'требования текст редактор', run: () => this.go(['/projects', current, 'requirements'])},
        {id: 'tab-runs', group: name, label: 'Запуски', hint: 'Агенты и результаты', icon: '@tui.history', keywords: 'запуски агенты история результаты', run: () => this.go(['/projects', current, 'runs'])},
      );
    }
    commands.push(
      {id: 'new', group: 'Действия', label: 'Новый проект', icon: '@tui.plus', keywords: 'создать новый проект добавить', run: () => this.go(['/projects/new'])},
      {id: 'all', group: 'Действия', label: 'Все проекты', icon: '@tui.layout-grid', keywords: 'проекты список все', run: () => this.go(['/projects'])},
      {
        id: 'theme',
        group: 'Действия',
        label: this.theme.dark() ? 'Светлая тема' : 'Тёмная тема',
        icon: this.theme.dark() ? '@tui.sun' : '@tui.moon',
        keywords: 'тема тёмная светлая ночь день',
        run: () => this.act(() => this.theme.toggle()),
      },
      {
        id: 'system-theme',
        group: 'Действия',
        label: 'Тема как в системе',
        icon: '@tui.refresh-cw',
        keywords: 'тема система авто',
        run: () => this.act(() => this.theme.followSystem()),
      },
    );
    for (const project of this.projects.items()) {
      if (project.id === current) continue;
      commands.push({
        id: `project-${project.id}`,
        group: 'Проекты',
        label: project.name,
        icon: '@tui.folder-open',
        keywords: project.name.toLowerCase(),
        run: () => this.go(['/projects', project.id]),
      });
    }
    return commands;
  });

  protected readonly results = computed(() => {
    const words = this.query().toLowerCase().trim().split(/\s+/).filter(Boolean);
    const matched = words.length
      ? this.commands().filter(command => words.every(word => `${command.label} ${command.keywords} ${command.group}`.toLowerCase().includes(word)))
      : this.commands();
    return matched.slice(0, 40);
  });

  protected readonly groups = computed(() => {
    const groups: {name: string; items: {command: Command; index: number}[]}[] = [];
    this.results().forEach((command, index) => {
      let group = groups.find(item => item.name === command.group);
      if (!group) {
        group = {name: command.group, items: []};
        groups.push(group);
      }
      group.items.push({command, index});
    });
    return groups;
  });

  protected readonly activeId = computed(() => {
    const command = this.results()[this.active()];
    return command ? `cmd-${command.id}` : null;
  });

  constructor() {
    this.projects.ensure();
  }

  protected onQuery(event: Event): void {
    this.query.set((event.target as HTMLInputElement).value);
    this.active.set(0);
  }

  protected onKeydown(event: KeyboardEvent): void {
    const count = this.results().length;
    if (!count) return;
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const delta = event.key === 'ArrowDown' ? 1 : -1;
      this.active.set((this.active() + delta + count) % count);
      queueMicrotask(() => this.list()?.nativeElement.querySelector('[aria-selected="true"]')?.scrollIntoView({block: 'nearest'}));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      this.results()[this.active()]?.run();
    }
  }

  protected pick(command: Command): void {
    command.run();
  }

  private go(commands: unknown[]): void {
    this.ref.close();
    void this.router.navigate(commands);
  }

  private act(effect: () => void): void {
    effect();
    this.ref.close();
  }
}
