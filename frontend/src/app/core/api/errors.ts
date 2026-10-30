import {HttpErrorResponse} from '@angular/common/http';

export type ErrorContext = 'project' | 'projects' | 'save' | 'job';

export interface ReadableError {
  title: string;
  hint: string;
  /** Повтор имеет смысл: сеть, недоступный сервис. */
  retryable: boolean;
  status: number | null;
}

const OFFLINE: ReadableError = {
  title: 'API не отвечает',
  hint: 'Проверьте, что контейнеры запущены: docker compose ps. Затем повторите.',
  retryable: true,
  status: 0,
};

/** Переводит ошибку HTTP в текст для человека: что случилось и что делать. */
export function readableError(error: unknown, context: ErrorContext): ReadableError {
  if (!(error instanceof HttpErrorResponse)) {
    return {title: 'Что-то пошло не так', hint: 'Обновите страницу. Если ошибка повторится, проверьте консоль браузера.', retryable: true, status: null};
  }
  const detail = typeof error.error?.detail === 'string' ? error.error.detail : '';
  switch (error.status) {
    case 0:
      return OFFLINE;
    case 404:
      if (context === 'job') {
        return {title: 'Агент не найден', hint: detail || 'Проверьте, что папка агента есть в agents/.', retryable: false, status: 404};
      }
      return {title: 'Проект не найден', hint: 'Возможно, его удалили или ссылка неверна. Вернитесь к списку проектов.', retryable: false, status: 404};
    case 422:
      return {
        title: 'Сервер не принял данные',
        hint: 'Название — от 1 до 200 символов, требования — от 1 до 50 000. Оба поля обязательны.',
        retryable: false,
        status: 422,
      };
    case 502:
    case 503:
    case 504:
      return {
        title: context === 'job' ? 'Очередь задач недоступна' : 'Сервис временно недоступен',
        hint: detail ? `${detail}. Проверьте docker compose logs worker-llm worker-build и повторите.` : 'Проверьте docker compose ps и повторите.',
        retryable: true,
        status: error.status,
      };
    default:
      return {
        title: `Ошибка сервера ${error.status}`,
        hint: detail || 'Повторите действие. Если ошибка не уйдёт, проверьте docker compose logs api.',
        retryable: error.status >= 500,
        status: error.status,
      };
  }
}
