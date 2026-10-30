import {AgentId} from './agents.catalog';

/**
 * Справочник этапов потока. Ключи совпадают с `STAGES` в backend/app/projects.py,
 * смысл этапов — с docs/architecture-overview.md (ветка docs).
 * Колонка и дорожка задают место станции на линии: разработка и проверки идут параллельными ветками.
 */
export type PhaseKey = 'analysis' | 'design' | 'build' | 'quality' | 'delivery';

export interface PhaseInfo {
  key: PhaseKey;
  name: string;
  /** Подпись для параллельных веток. */
  parallel?: string;
}

export const PHASES: readonly PhaseInfo[] = [
  {key: 'analysis', name: 'Анализ'},
  {key: 'design', name: 'Интерфейс'},
  {key: 'build', name: 'Разработка', parallel: 'параллельно'},
  {key: 'quality', name: 'Качество', parallel: 'параллельно'},
  {key: 'delivery', name: 'Поставка'},
];

export interface StageInfo {
  key: string;
  /** Короткая подпись для линии. */
  short: string;
  phase: PhaseKey;
  column: number;
  lane: number;
  question: string;
  summary: string;
  input: string;
  output: string;
  check: string;
  agent: AgentId | null;
  /** Инструкция этапа, которую Студия добавляет перед требованиями при запуске агента. */
  preset: string | null;
}

export const STAGE_CATALOG: readonly StageInfo[] = [
  {
    key: 'business_analysis',
    short: 'Бизнес-анализ',
    phase: 'analysis',
    column: 0,
    lane: 0,
    question: 'Что нужно и зачем?',
    summary: 'Разбирает требования, находит пробелы и неоднозначности, задаёт вопросы или фиксирует допущения.',
    input: 'Текст требований и приложенные данные',
    output: 'Требования, вопросы, допущения, истории, бизнес-правила и критерии приёмки',
    check: 'У каждого бизнес-правила есть критерий приёмки',
    agent: 'analyst',
    preset:
      'Проведи бизнес-анализ требований ниже. Выдели цель, роли пользователей, основные сценарии, бизнес-правила, ' +
      'неоднозначности и допущения, которые придётся принять. Ответь кратким структурированным резюме.',
  },
  {
    key: 'system_analysis',
    short: 'Системный анализ',
    phase: 'analysis',
    column: 1,
    lane: 0,
    question: 'Как это устроено?',
    summary: 'Описывает сущности, состояния, роли и права, API, события и интеграции.',
    input: 'Результат бизнес-анализа',
    output: 'Модель приложения, OpenAPI, AsyncAPI, диаграммы состояний',
    check: 'Схема и линтер модели',
    agent: 'analyst',
    preset:
      'Проведи системный анализ требований ниже: сущности и связи, машины состояний, роли и права, ' +
      'команды и запросы API, доменные события и внешние интеграции.',
  },
  {
    key: 'interfaces',
    short: 'Интерфейсы',
    phase: 'design',
    column: 2,
    lane: 0,
    question: 'Как это выглядит?',
    summary: 'Проектирует экраны по ролям и платформам, тексты и состояния экранов.',
    input: 'Модель приложения',
    output: 'Описание экранов и пользовательских путей',
    check: 'Каждую пользовательскую историю можно пройти по экранам',
    agent: 'analyst',
    preset:
      'Спроектируй интерфейсы по требованиям ниже: экраны для каждой роли и платформы, ключевые элементы, ' +
      'тексты и состояния «загрузка», «пусто», «ошибка».',
  },
  {
    key: 'frontend',
    short: 'Frontend',
    phase: 'build',
    column: 3,
    lane: -1,
    question: 'Как устроена админка?',
    summary: 'Генератор собирает каркас Angular, агент дописывает нетиповую логику.',
    input: 'Описание экранов и контракты API',
    output: 'Код административного веб-интерфейса',
    check: 'Сборка и тесты из критериев приёмки',
    agent: 'developer',
    preset: 'Реализуй нетиповую логику административного интерфейса в каталоге admin-web/src/app/custom по требованиям ниже.',
  },
  {
    key: 'backend',
    short: 'Backend',
    phase: 'build',
    column: 3,
    lane: 0,
    question: 'Как работает сервер?',
    summary: 'Генератор собирает каркас ASP.NET Core, агент пишет хуки бизнес-правил.',
    input: 'Модель приложения и тесты',
    output: 'Код бэкенда и хуки правил',
    check: 'Сборка и тесты из критериев приёмки',
    agent: 'developer',
    preset: 'Реализуй хуки бизнес-правил в каталоге backend/src/App.Domain/Hooks так, чтобы тесты стали зелёными.',
  },
  {
    key: 'database',
    short: 'База данных',
    phase: 'build',
    column: 3,
    lane: 1,
    question: 'Где живут данные?',
    summary: 'Таблицы и миграции выводятся из модели, агент готовит тестовые данные.',
    input: 'Сущности модели',
    output: 'Миграции и тестовые данные',
    check: 'Миграции применяются на пустой базе',
    agent: 'developer',
    preset: 'Подготовь тестовые данные для демонстрационного сценария в каталоге db/seed по требованиям ниже.',
  },
  {
    key: 'testing',
    short: 'Тесты',
    phase: 'quality',
    column: 4,
    lane: -0.5,
    question: 'Работает ли по требованиям?',
    summary: 'Тесты пишутся из критериев приёмки до кода и обязаны сначала падать.',
    input: 'Критерии приёмки и контракты',
    output: 'Тесты и отчёт о том, что каждый тест умеет падать',
    check: 'Каждый тест бизнес-правила падает на каркасе без логики',
    agent: null,
    preset: null,
  },
  {
    key: 'security',
    short: 'Безопасность',
    phase: 'quality',
    column: 4,
    lane: 0.5,
    question: 'Нет ли уязвимостей?',
    summary: 'Сканеры проверяют код, зависимости, секреты и контейнеры.',
    input: 'Код и образы',
    output: 'Отчёты сканеров',
    check: 'Нет находок уровня high и critical',
    agent: null,
    preset: null,
  },
  {
    key: 'cicd',
    short: 'CI/CD',
    phase: 'delivery',
    column: 5,
    lane: 0,
    question: 'Запускается ли у пользователя?',
    summary: 'GitLab CI собирает образы, разворачивает стенд и проходит демонстрационный сценарий.',
    input: 'Код и тесты',
    output: 'Зелёный пайплайн, адрес стенда, APK',
    check: 'Проверка здоровья и E2E демонстрационного сценария',
    agent: null,
    preset: null,
  },
  {
    key: 'documentation',
    short: 'Документация',
    phase: 'delivery',
    column: 6,
    lane: 0,
    question: 'Понятно ли, что сделано?',
    summary: 'Собирает системную, продуктовую и пользовательскую документацию и отчёт о расходе.',
    input: 'Все артефакты прогона',
    output: 'Сайт документации, паспорт прототипа, отчёт о токенах и времени',
    check: 'Упомянуты все критерии приёмки и роли',
    agent: 'analyst',
    preset: 'Подготовь краткую документацию по требованиям ниже: назначение продукта, роли, основные сценарии и ограничения.',
  },
];

const BY_KEY = new Map(STAGE_CATALOG.map(stage => [stage.key, stage]));

export function stageInfo(key: string | null | undefined): StageInfo | null {
  return key ? BY_KEY.get(key) ?? null : null;
}

export function phaseInfo(key: PhaseKey): PhaseInfo {
  return PHASES.find(phase => phase.key === key) ?? PHASES[0];
}
