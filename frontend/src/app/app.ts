import {CdkTrapFocus} from '@angular/cdk/a11y';
import {Dialog} from '@angular/cdk/dialog';
import {ChangeDetectionStrategy, Component, computed, DestroyRef, effect, ElementRef, inject, signal, viewChild} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet} from '@angular/router';
import {TuiButton, TuiHint, TuiIcon, TuiRoot} from '@taiga-ui/core';
import {filter} from 'rxjs';
import {jobStatusView, Tone} from './core/pipeline/status';
import {HealthService} from './core/state/health.service';
import {JobsStore} from './core/state/jobs.store';
import {ProjectsStore} from './core/state/projects.store';
import {ShellService} from './core/state/shell.service';
import {ThemeService} from './core/state/theme.service';
import {CommandPalette} from './features/shell/command-palette';
import {BrandMark} from './shared/ui/brand-mark';
import {ToastHost} from './shared/ui/toast-host';

const RECENT_LIMIT = 8;

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CdkTrapFocus, TuiRoot, TuiButton, TuiIcon, TuiHint, BrandMark, ToastHost],
  templateUrl: './app.html',
  styleUrl: './app.less',
  host: {'(document:keydown)': 'onKeydown($event)'},
})
export class App {
  protected readonly shell = inject(ShellService);
  protected readonly theme = inject(ThemeService);
  protected readonly health = inject(HealthService);
  protected readonly projects = inject(ProjectsStore);
  private readonly jobs = inject(JobsStore);
  private readonly dialog = inject(Dialog);
  private readonly menuButton = viewChild<ElementRef<HTMLElement>>('menuButton');
  private readonly host: ElementRef<HTMLElement> = inject(ElementRef);

  protected readonly isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
  /** Боковая панель как выезжающее меню на узких экранах. */
  protected readonly menuOpen = signal(false);
  /** На ноутбуках панель сжимается до иконок, чтобы граф этапов помещался по ширине. */
  private readonly railQuery = matchMedia('(min-width: 1024px) and (max-width: 1439.98px)');
  protected readonly rail = signal(this.railQuery.matches);

  /** Недавние проекты с тоном последнего запуска: видно, где агент работает прямо сейчас. */
  protected readonly recent = computed(() =>
    [...this.projects.items()]
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
      .slice(0, RECENT_LIMIT)
      .map(project => {
        const views = this.jobs.list(project.id).map(run => jobStatusView(run.status, run.subtype, run.stale));
        const live = views.some(view => view.live);
        const tone: Tone = live ? 'run' : (views[0]?.tone ?? 'idle');
        return {project, tone, live, initial: project.name.trim().charAt(0).toUpperCase() || '·'};
      }),
  );

  protected readonly healthLabel = computed(() => {
    switch (this.health.state()) {
      case 'ok':
        return 'API на связи';
      case 'down':
        return 'API не отвечает';
      default:
        return 'Проверяем API';
    }
  });
  protected readonly healthHint = computed(() =>
    this.health.state() === 'down'
      ? 'Запустите бэкенд: docker compose up -d. Студия проверяет связь каждые несколько секунд.'
      : 'Студия проверяет /api/health каждые 20 секунд.',
  );

  constructor() {
    this.projects.ensure();
    const onRail = () => this.rail.set(this.railQuery.matches);
    this.railQuery.addEventListener('change', onRail);
    inject(DestroyRef).onDestroy(() => this.railQuery.removeEventListener('change', onRail));
    // Открытое меню забирает фокус: первым становится знак «Поток»
    effect(() => {
      if (this.menuOpen()) setTimeout(() => this.host.nativeElement.querySelector<HTMLElement>('#sidebar a')?.focus());
    });
    inject(Router)
      .events.pipe(
        filter(event => event instanceof NavigationEnd),
        takeUntilDestroyed(),
      )
      .subscribe(() => this.menuOpen.set(false));
  }

  protected closeMenu(): void {
    if (!this.menuOpen()) return;
    this.menuOpen.set(false);
    this.menuButton()?.nativeElement.focus();
  }

  protected openPalette(): void {
    this.menuOpen.set(false);
    if (this.dialog.openDialogs.some(ref => ref.componentInstance instanceof CommandPalette)) return;
    this.dialog.open(CommandPalette, {
      backdropClass: 'dialog-backdrop',
      panelClass: ['dialog-panel', 'palette-panel'],
      autoFocus: 'first-tabbable',
      restoreFocus: true,
      ariaLabel: 'Поиск и команды',
    });
  }

  protected onKeydown(event: KeyboardEvent): void {
    if ((event.metaKey || event.ctrlKey) && !event.altKey && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      this.openPalette();
    }
  }
}
