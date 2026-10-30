import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  ElementRef,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import {TuiIcon} from '@taiga-ui/core';
import {PHASES, PhaseKey} from '../../../core/pipeline/stages.catalog';
import {byPlace, connector, FlowStation, hasAgent, stationNote, toneIcon} from './flow.model';

interface GraphNode extends FlowStation {
  x: number;
  y: number;
  width: number;
  note: string;
  icon: string;
}

interface GraphEdge {
  id: string;
  d: string;
  done: boolean;
  dashed: boolean;
}

interface GraphPhase {
  key: PhaseKey;
  name: string;
  x: number;
  width: number;
}

interface GraphLayout {
  nodes: GraphNode[];
  edges: GraphEdge[];
  phases: GraphPhase[];
  width: number;
  height: number;
}

// Геометрия узлов в пикселях: граф рисуется один к одному, без масштабирования
const NODE_H = 52;
const LANE_GAP = 12;
const GAP_MIN = 20;
const GAP_MAX = 64;
const NODE_CHROME = 1 + 10 + 16 + 8 + 12 + 1; // рамка, поле слева, иконка, промежуток, поле справа, рамка
const NODE_MIN = 108;
const PHASES_H = 32;
const NAME_FONT = '500 13px "Inter Variable", Inter, system-ui, sans-serif';
const NOTE_FONT = '400 12px "Inter Variable", Inter, system-ui, sans-serif';

/**
 * Линия этапов — граф пайплайна, как в GitHub Actions: колонки этапов, параллельные этапы друг под другом,
 * ортогональные связи. Если граф не помещается по ширине, он становится вертикальным таймлайном.
 * Узлы — кнопки; стрелки на клавиатуре переключают выбранный этап.
 */
@Component({
  selector: 'app-flow-map',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiIcon],
  templateUrl: './flow-map.html',
  styleUrl: './flow-map.less',
  host: {
    '[class.is-vertical]': 'vertical()',
    '[class.is-static]': '!interactive()',
    '[attr.aria-hidden]': 'interactive() ? null : "true"',
    '(keydown)': 'onKeydown($event)',
  },
})
export class FlowMap {
  readonly stations = input.required<FlowStation[]>();
  readonly selected = input<string | null>(null);
  readonly interactive = input(true);
  readonly label = input('Линия этапов');
  /** id панели, которую описывает выбранный этап. */
  readonly controls = input<string | null>(null);
  readonly select = output<string>();

  private readonly host: ElementRef<HTMLElement> = inject(ElementRef);
  private readonly width = signal(0);
  /** Пересчитать ширины узлов, когда загрузится шрифт. */
  private readonly fontsReady = signal(false);
  private readonly measure = textMeasurer();

  protected readonly ordered = computed(() => [...this.stations()].sort(byPlace));
  protected readonly focusKey = computed(() => this.selected() ?? this.ordered()[0]?.key ?? null);

  protected readonly layout = computed<GraphLayout | null>(() => {
    this.fontsReady();
    const available = this.width();
    const ordered = this.ordered();
    if (!available || !ordered.length) return null;

    const columns = [...new Set(ordered.map(station => station.column))].sort((a, b) => a - b);
    const byColumn = columns.map(column => ordered.filter(station => station.column === column));
    const widths = byColumn.map(group =>
      Math.max(
        NODE_MIN,
        ...group.map(station =>
          Math.ceil(Math.max(this.measure(station.label, NAME_FONT), this.measure(stationNote(station), NOTE_FONT)) + NODE_CHROME),
        ),
      ),
    );
    const content = widths.reduce((sum, width) => sum + width, 0);
    const gaps = Math.max(1, columns.length - 1);
    const gap = Math.min(GAP_MAX, (available - content) / gaps);
    if (gap < GAP_MIN) return null;

    const tallest = Math.max(...byColumn.map(group => group.length));
    const graphH = tallest * NODE_H + (tallest - 1) * LANE_GAP;
    const xs: number[] = [];
    let cursor = 0;
    for (const width of widths) {
      xs.push(cursor);
      cursor += width + gap;
    }
    const totalW = cursor - gap;

    const nodes: GraphNode[] = byColumn.flatMap((group, index) => {
      const top = PHASES_H + (graphH - (group.length * NODE_H + (group.length - 1) * LANE_GAP)) / 2;
      return group.map((station, lane) => ({
        ...station,
        x: xs[index],
        y: top + lane * (NODE_H + LANE_GAP),
        width: widths[index],
        note: stationNote(station),
        icon: toneIcon(station.tone, station.live),
      }));
    });

    const edges: GraphEdge[] = [];
    byColumn.forEach((group, index) => {
      if (index === byColumn.length - 1) return;
      const xm = xs[index] + widths[index] + gap / 2;
      for (const from of group) {
        const a = nodes.find(node => node.key === from.key)!;
        for (const to of byColumn[index + 1]) {
          const b = nodes.find(node => node.key === to.key)!;
          edges.push({
            id: `${a.key}>${b.key}`,
            d: connector(a.x + a.width, a.y + NODE_H / 2, b.x, b.y + NODE_H / 2, xm),
            done: a.tone === 'ok',
            dashed: !hasAgent(b),
          });
        }
      }
    });
    // Пройденные связи рисуются поверх остальных
    edges.sort((a, b) => Number(a.done) - Number(b.done));

    const phases: GraphPhase[] = [];
    for (const phase of PHASES) {
      const members = nodes.filter(node => node.phase === phase.key);
      if (!members.length) continue;
      const left = Math.min(...members.map(node => node.x));
      const right = Math.max(...members.map(node => node.x + node.width));
      phases.push({key: phase.key, name: phase.name, x: left, width: right - left});
    }

    return {nodes, edges, phases, width: totalW, height: PHASES_H + graphH};
  });

  protected readonly vertical = computed(() => this.width() > 0 && !this.layout());

  /** Вертикальный таймлайн: фазы сверху вниз, параллельные этапы отмечены. */
  protected readonly groups = computed(() =>
    PHASES.map(phase => {
      const nodes = this.ordered()
        .filter(station => station.phase === phase.key)
        .map(station => ({...station, note: stationNote(station), icon: toneIcon(station.tone, station.live)}));
      const parallel = nodes.length > 1 && new Set(nodes.map(node => node.column)).size === 1;
      return {key: phase.key, name: phase.name, parallel, nodes};
    }).filter(group => group.nodes.length),
  );

  constructor() {
    const destroyRef = inject(DestroyRef);
    afterNextRender(() => {
      const element = this.host.nativeElement;
      this.width.set(element.clientWidth);
      const observer = new ResizeObserver(([entry]) => this.width.set(Math.floor(entry.contentRect.width)));
      observer.observe(element);
      destroyRef.onDestroy(() => observer.disconnect());
      // Пока Inter грузится, canvas меряет запасным шрифтом: после загрузки ширины считаются заново
      document.fonts?.load(NAME_FONT).then(
        () => {
          this.measure.reset();
          this.fontsReady.set(true);
        },
        () => undefined,
      );
    });
  }

  protected choose(key: string): void {
    if (this.interactive()) this.select.emit(key);
  }

  protected onKeydown(event: KeyboardEvent): void {
    if (!this.interactive()) return;
    const order = this.ordered();
    const current = order.findIndex(station => station.key === this.focusKey());
    if (current < 0) return;
    let next = current;
    const here = order[current];
    switch (event.key) {
      case 'ArrowRight':
        next = Math.min(order.length - 1, current + 1);
        break;
      case 'ArrowLeft':
        next = Math.max(0, current - 1);
        break;
      case 'ArrowDown':
        next = this.vertical() ? Math.min(order.length - 1, current + 1) : this.sameColumn(order, here, 1, current);
        break;
      case 'ArrowUp':
        next = this.vertical() ? Math.max(0, current - 1) : this.sameColumn(order, here, -1, current);
        break;
      case 'Home':
        next = 0;
        break;
      case 'End':
        next = order.length - 1;
        break;
      default:
        return;
    }
    event.preventDefault();
    const key = order[next].key;
    this.select.emit(key);
    queueMicrotask(() => this.host.nativeElement.querySelector<HTMLElement>(`[data-key="${key}"]`)?.focus());
  }

  private sameColumn(order: FlowStation[], here: FlowStation, direction: 1 | -1, fallback: number): number {
    const lanes = order.filter(station => station.column === here.column);
    const target = lanes[lanes.indexOf(here) + direction];
    return target ? order.indexOf(target) : fallback;
  }
}

interface TextMeasurer {
  (text: string, font: string): number;
  reset(): void;
}

/** Ширина текста через canvas: раскладка графа считается до отрисовки, без замеров DOM. */
function textMeasurer(): TextMeasurer {
  const context = document.createElement('canvas').getContext('2d');
  const cache = new Map<string, number>();
  const measure = (text: string, font: string) => {
    const key = `${font}|${text}`;
    const known = cache.get(key);
    if (known !== undefined) return known;
    if (!context) return text.length * 7.5;
    context.font = font;
    const width = context.measureText(text).width;
    cache.set(key, width);
    return width;
  };
  return Object.assign(measure, {reset: () => cache.clear()});
}
