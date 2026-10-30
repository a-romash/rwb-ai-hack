import {AgentId} from './agents.catalog';

/**
 * Конвейер RWB: фиксированная цепочка шагов с номерами этапов кейса Э1–Э7 и воротами качества G0–G5.
 * Повторяет `harness/registry.py` (ветка main, поставка M0): ключи, порядок, ворота и участники совпадают.
 * Смысл ворот — из раздела 11.6 решения «Трасса».
 */
export type StageKey = 'analysis' | 'spec' | 'ui' | 'scaffold' | 'tests' | 'develop' | 'verify' | 'report';
export type GateKey = 'G0' | 'G1' | 'G1.5' | 'G2' | 'G3' | 'G4' | 'G5';
export type Autonomy = 'A0' | 'A1' | 'A2';

export interface StageInfo {
  key: StageKey;
  /** Номер этапа в кейсе RWB. */
  code: string;
  title: string;
  /** Короткая подпись — то же, что title: поле осталось для мест, где этап упоминается в строке. */
  short: string;
  queue: 'llm' | 'build';
  gates: readonly GateKey[];
  /** Этапы проекта из backend/app/projects.py, которые участвуют в шаге. */
  participants: readonly string[];
  question: string;
  summary: string;
  input: string;
  output: string;
  agent: AgentId | null;
  /** Инструкция шага, которую Студия добавляет перед требованиями при запуске агента. */
  preset: string | null;
  /** Шаг выполняется, даже если прогон остановился раньше. */
  always?: boolean;
}

export interface GateInfo {
  key: GateKey;
  name: string;
  check: string;
  decider: string;
  onFail: string;
}

export const STAGE_CATALOG: readonly StageInfo[] = [
  {
    key: 'analysis',
    code: 'Э1',
    title: 'Анализ требований',
    short: 'Анализ требований',
    queue: 'llm',
    gates: ['G0'],
    participants: ['business_analysis'],
    question: 'Что нужно и зачем?',
    summary: 'Разбирает требования и приложенные файлы, находит пробелы и неоднозначности, задаёт вопросы и фиксирует допущения.',
    input: 'Текст требований и приложенные файлы',
    output: 'Требования, вопросы, допущения и глоссарий',
    agent: 'analyst',
    preset:
      'Проведи бизнес-анализ требований ниже. Выдели цель, роли пользователей, основные сценарии, бизнес-правила, ' +
      'неоднозначности и допущения, которые придётся принять. Ответь кратким структурированным резюме.',
  },
  {
    key: 'spec',
    code: 'Э2',
    title: 'Системный анализ',
    short: 'Системный анализ',
    queue: 'llm',
    gates: ['G1'],
    participants: ['system_analysis', 'database'],
    question: 'Как это устроено?',
    summary: 'Строит модель предметной области: сущности, бизнес-правила, события, API и интеграции, — и проверяет её валидаторами.',
    input: 'Требования и ответы на вопросы',
    output: 'Модель домена, правила, OpenAPI, AsyncAPI, нефункциональные требования',
    agent: 'analyst',
    preset:
      'Проведи системный анализ требований ниже: сущности и связи, машины состояний, роли и права, ' +
      'команды и запросы API, доменные события и внешние интеграции.',
  },
  {
    key: 'ui',
    code: 'Э3',
    title: 'Интерфейсы',
    short: 'Интерфейсы',
    queue: 'llm',
    gates: ['G1.5'],
    participants: ['interfaces'],
    question: 'Как с этим работать?',
    summary: 'Проектирует экраны для каждого сценария и роли, их состояния и тексты интерфейса.',
    input: 'Сценарии и модель домена',
    output: 'Описание экранов, тексты, превью',
    agent: 'analyst',
    preset:
      'Спроектируй интерфейсы по требованиям ниже: экраны для каждой роли и платформы, ключевые элементы, ' +
      'тексты и состояния «загрузка», «пусто», «ошибка».',
  },
  {
    key: 'scaffold',
    code: 'Э4',
    title: 'Каркас приложения',
    short: 'Каркас приложения',
    queue: 'build',
    gates: [],
    participants: ['frontend', 'backend', 'database', 'cicd'],
    question: 'На чём строим?',
    summary: 'Генераторы собирают каркас бэкенда, админки и мобильного клиента, заглушки и конфигурацию развёртывания.',
    input: 'Спецификация и описание экранов',
    output: 'Каркас backend, admin и mobile, моки, deploy',
    agent: 'developer',
    preset: 'Собери каркас приложения по требованиям ниже: структуру backend и admin, заглушки бизнес-правил и конфигурацию запуска.',
  },
  {
    key: 'tests',
    code: 'Э5',
    title: 'Тесты приёмки',
    short: 'Тесты приёмки',
    queue: 'build',
    gates: ['G2'],
    participants: ['testing'],
    question: 'Как поймём, что готово?',
    summary: 'Тесты пишутся из критериев приёмки до кода. Каждый тест бизнес-правила обязан сначала упасть на каркасе.',
    input: 'Критерии приёмки и каркас',
    output: 'Тесты приёмки',
    agent: null,
    preset: null,
  },
  {
    key: 'develop',
    code: 'Э4',
    title: 'Разработка',
    short: 'Разработка',
    queue: 'build',
    gates: [],
    participants: ['backend', 'frontend'],
    question: 'Как это сделать?',
    summary: 'Агент наполняет каркас логикой, пока тесты приёмки не станут зелёными.',
    input: 'Каркас и тесты приёмки',
    output: 'Код backend и admin',
    agent: 'developer',
    preset: 'Реализуй хуки бизнес-правил в каталоге backend/src/App.Domain/Hooks так, чтобы тесты приёмки стали зелёными.',
  },
  {
    key: 'verify',
    code: 'Э5–Э6',
    title: 'Проверки и стенд',
    short: 'Проверки и стенд',
    queue: 'build',
    gates: ['G3', 'G4'],
    participants: ['testing', 'security', 'cicd'],
    question: 'Можно ли выпускать?',
    summary: 'Прогоняет тесты, линтеры и проверки безопасности, собирает образы и поднимает стенд.',
    input: 'Код и тесты',
    output: 'Отчёты тестов и безопасности, образы, адрес стенда',
    agent: null,
    preset: null,
  },
  {
    key: 'report',
    code: 'Э7',
    title: 'Отчёт',
    short: 'Отчёт',
    queue: 'llm',
    gates: ['G5'],
    participants: ['documentation'],
    question: 'Что получилось?',
    summary: 'Собирает документацию, паспорт решения и отчёт о расходе токенов и времени.',
    input: 'Артефакты всех шагов',
    output: 'Документация, паспорт, отчёт прогона',
    agent: 'analyst',
    preset: 'Подготовь краткую документацию по требованиям ниже: назначение продукта, роли, основные сценарии и ограничения.',
    always: true,
  },
];

export const GATES: Record<GateKey, GateInfo> = {
  G0: {
    key: 'G0',
    name: 'Входы',
    check: 'Все файлы разобраны, у каждого требования есть якорь — фрагмент источника',
    decider: 'Код',
    onFail: 'Повторный разбор; файл без текста помечается в отчёте',
  },
  G1: {
    key: 'G1',
    name: 'Спецификация',
    check: 'Валидаторы модели зелёные, вопросы закрыты ответами или допущениями',
    decider: 'Код, в режимах A0 и A1 — ещё и человек',
    onFail: 'Точечные исправления, не больше трёх кругов; затем элементы помечаются «под вопросом»',
  },
  'G1.5': {
    key: 'G1.5',
    name: 'Сценарии и экраны',
    check: 'У каждого сценария есть экран, у каждого экрана — состояния',
    decider: 'Код',
    onFail: 'Исправление описания экранов',
  },
  G2: {
    key: 'G2',
    name: 'Red-proof',
    check: 'Каждый тест бизнес-правила падает на каркасе с заглушками',
    decider: 'Код',
    onFail: 'Тест возвращается на доработку, не больше двух раз; затем «тест под вопросом»',
  },
  G3: {
    key: 'G3',
    name: 'Сборка и проверки',
    check: 'Тесты приёмки зелёные, линтеры чистые, нет уязвимостей high и critical, секретов нет',
    decider: 'Код',
    onFail: 'Возврат в разработку в пределах бюджета; затем частичный результат',
  },
  G4: {
    key: 'G4',
    name: 'Стенд',
    check: 'Health, smoke и E2E по ролям проходят на развёрнутом стенде',
    decider: 'Код',
    onFail: 'Повторный деплой или откат; затем «не развёрнуто» в паспорте',
  },
  G5: {
    key: 'G5',
    name: 'Приёмка',
    check: 'Человек прошёл сценарий своей роли — в режиме A2 приёмка автоматическая',
    decider: 'Человек или код',
    onFail: 'Запрос изменения и новая версия спецификации',
  },
};

/** Уровни автономии из кейса: где в прогоне участвует человек. */
export const AUTONOMY: Record<Autonomy, {name: string; human: string}> = {
  A0: {name: 'Пошагово', human: 'Утверждает каждый шаг'},
  A1: {name: 'Только важное', human: 'Отвечает на вопросы и замораживает спецификацию'},
  A2: {name: 'Полный автомат', human: 'Не участвует: вопросы закрываются ответами по умолчанию'},
};

/** Подписи этапов проекта, которые участвуют в шагах конвейера. */
export const PARTICIPANTS: Record<string, string> = {
  business_analysis: 'Бизнес-анализ',
  system_analysis: 'Системный анализ',
  interfaces: 'Интерфейсы',
  frontend: 'Frontend',
  backend: 'Backend',
  database: 'База данных',
  testing: 'Тестирование',
  security: 'Безопасность',
  cicd: 'CI/CD',
  documentation: 'Документация',
};

/** Запуски, сохранённые до перехода на конвейер RWB, ссылались на этапы проекта: показываем их на шаге, где этап участвует. */
const LEGACY: Record<string, StageKey> = {
  business_analysis: 'analysis',
  system_analysis: 'spec',
  database: 'spec',
  interfaces: 'ui',
  frontend: 'develop',
  backend: 'develop',
  testing: 'tests',
  security: 'verify',
  cicd: 'verify',
  documentation: 'report',
};

const BY_KEY = new Map<string, StageInfo>(STAGE_CATALOG.map(stage => [stage.key, stage]));

export function normalizeStageKey(key: string | null | undefined): StageKey | null {
  if (!key) return null;
  if (BY_KEY.has(key)) return key as StageKey;
  return LEGACY[key] ?? null;
}

export function stageInfo(key: string | null | undefined): StageInfo | null {
  const normalized = normalizeStageKey(key);
  return normalized ? BY_KEY.get(normalized) ?? null : null;
}

export function gateInfo(key: string | null | undefined): GateInfo | null {
  return key && key in GATES ? GATES[key as GateKey] : null;
}
