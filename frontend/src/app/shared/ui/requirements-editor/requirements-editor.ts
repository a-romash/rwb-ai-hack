import {
  afterRenderEffect,
  ChangeDetectionStrategy,
  Component,
  computed,
  ElementRef,
  input,
  model,
  output,
  signal,
  viewChild,
} from '@angular/core';
import {TuiButton, TuiHint} from '@taiga-ui/core';
import {countWords, estimateTokens, formatNumber, plural} from '../../../core/util/text';

const MAX_FILE_BYTES = 400_000;

/**
 * Редактор требований как документ: удобная ширина строки, автовысота, импорт файла,
 * перетаскивание, шаблон разделов и счётчики. О сохранении ничего не знает.
 */
@Component({
  selector: 'app-requirements-editor',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TuiButton, TuiHint],
  templateUrl: './requirements-editor.html',
  styleUrl: './requirements-editor.less',
  host: {
    '[class.is-dragging]': 'dragging()',
    '[class.is-invalid]': 'invalid()',
    '(dragenter)': 'onDrag($event, true)',
    '(dragover)': 'onDrag($event, true)',
    '(dragleave)': 'onDragLeave($event)',
    '(drop)': 'onDrop($event)',
  },
})
export class RequirementsEditor {
  readonly value = model('');
  readonly maxLength = input(50_000);
  readonly inputId = input('requirements');
  readonly placeholder = input('Опишите продукт: зачем он нужен, кто им пользуется, что должен уметь и как понять, что всё готово.');
  readonly invalid = input(false);
  readonly describedBy = input<string | null>(null);
  /** Предложить пример, пока документ пуст. */
  readonly offerExample = input(true);

  readonly insertTemplate = output<void>();
  readonly insertExample = output<void>();
  readonly fileError = output<string>();

  private readonly area = viewChild.required<ElementRef<HTMLTextAreaElement>>('area');
  private readonly fileInput = viewChild.required<ElementRef<HTMLInputElement>>('file');
  protected readonly dragging = signal(false);

  protected readonly length = computed(() => this.value().length);
  protected readonly empty = computed(() => !this.value().trim());
  protected readonly stats = computed(() => {
    const text = this.value();
    const words = countWords(text);
    return {
      chars: formatNumber(text.length),
      max: formatNumber(this.maxLength()),
      words: `${formatNumber(words)} ${plural(words, ['слово', 'слова', 'слов'])}`,
      tokens: formatNumber(estimateTokens(text)),
    };
  });
  protected readonly load = computed(() => {
    const ratio = this.length() / this.maxLength();
    return ratio >= 1 ? 'fail' : ratio >= 0.9 ? 'wait' : 'idle';
  });

  constructor() {
    // Автовысота: поле растёт вместе с текстом, страница прокручивается целиком
    afterRenderEffect(() => {
      this.value();
      const area = this.area().nativeElement;
      area.style.height = 'auto';
      area.style.height = `${area.scrollHeight}px`;
    });
  }

  focus(): void {
    this.area().nativeElement.focus();
  }

  protected onInput(event: Event): void {
    this.value.set((event.target as HTMLTextAreaElement).value);
  }

  protected pickFile(): void {
    this.fileInput().nativeElement.click();
  }

  protected onFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) void this.read(file);
    input.value = '';
  }

  protected onDrag(event: DragEvent, over: boolean): void {
    if (!event.dataTransfer?.types.includes('Files')) return;
    event.preventDefault();
    this.dragging.set(over);
  }

  protected onDragLeave(event: DragEvent): void {
    const host = event.currentTarget as HTMLElement;
    if (!host.contains(event.relatedTarget as Node | null)) this.dragging.set(false);
  }

  protected onDrop(event: DragEvent): void {
    const file = event.dataTransfer?.files?.[0];
    if (!file) return;
    event.preventDefault();
    this.dragging.set(false);
    void this.read(file);
  }

  private async read(file: File): Promise<void> {
    const textual = /\.(md|markdown|txt)$/i.test(file.name) || file.type.startsWith('text/');
    if (!textual) {
      this.fileError.emit('Подойдёт текстовый файл: .md или .txt. Текст из PDF и Word пока вставляйте вручную.');
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      this.fileError.emit('Файл больше 400 КБ. Сократите текст до 50 000 символов.');
      return;
    }
    const text = (await file.text()).replace(/\r\n/g, '\n').trim();
    const merged = this.empty() ? text : `${this.value().trimEnd()}\n\n${text}`;
    if (merged.length > this.maxLength()) {
      this.fileError.emit(`После вставки получится ${formatNumber(merged.length)} символов — больше лимита 50 000.`);
      return;
    }
    this.value.set(merged);
    this.focus();
  }
}
