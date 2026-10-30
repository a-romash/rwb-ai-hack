import {Page, Route} from '@playwright/test';

/** Подмена API Студии. Форма ответов повторяет backend/app/schemas.py. */

export const STAGES: [string, string][] = [
  ['business_analysis', 'Бизнес-анализ'],
  ['system_analysis', 'Системный анализ'],
  ['interfaces', 'Проектирование интерфейсов'],
  ['frontend', 'Frontend'],
  ['backend', 'Backend'],
  ['database', 'База данных'],
  ['testing', 'Тестирование'],
  ['security', 'Безопасность'],
  ['cicd', 'CI/CD'],
  ['documentation', 'Документация'],
];

export interface MockProject {
  id: string;
  name: string;
  requirements: string;
  created_at: string;
  updated_at: string;
  stages: {id: string; key: string; name: string; position: number; status: string}[];
}

export interface JobStep {
  status: string;
  subtype?: string | null;
  result?: string | null;
  num_turns?: number | null;
}

export interface MockOptions {
  projects?: MockProject[];
  /** Статусы, которые по очереди вернёт опрос задачи; последний повторяется. */
  jobSteps?: JobStep[];
  failList?: boolean;
  /** Прогоны конвейера проекта (`/api/projects/{id}/runs`); первый — последний. */
  runs?: Record<string, unknown>[];
  /** Уже приложенные к проекту файлы (`/api/projects/{id}/attachments`). */
  attachments?: {name: string; size: number}[];
}

export interface MockApi {
  projects: MockProject[];
  requests: {method: string; url: string; body: unknown}[];
}

export function makeProject(name: string, requirements = 'Сотрудник создаёт заявку, руководитель согласует.', id = crypto.randomUUID()): MockProject {
  const now = new Date().toISOString();
  return {
    id,
    name,
    requirements,
    created_at: now,
    updated_at: now,
    stages: STAGES.map(([key, label], index) => ({id: `${id}-${key}`, key, name: label, position: index + 1, status: 'not_started'})),
  };
}

function summary(project: MockProject) {
  const {id, name, created_at, updated_at} = project;
  return {id, name, created_at, updated_at};
}

export async function mockApi(page: Page, options: MockOptions = {}): Promise<MockApi> {
  const state: MockApi = {projects: [...(options.projects ?? [])], requests: []};
  const steps = options.jobSteps ?? [{status: 'success', subtype: 'success', result: '{"summary":"Готово"}', num_turns: 1}];
  let polls = 0;

  const log = (route: Route) => {
    const request = route.request();
    let body: unknown = null;
    try {
      body = request.postDataJSON();
    } catch {
      body = request.postData();
    }
    state.requests.push({method: request.method(), url: request.url(), body});
  };

  await page.route('**/api/health', route => route.fulfill({json: {status: 'ok'}}));

  await page.route('**/api/projects', async route => {
    log(route);
    const method = route.request().method();
    if (method === 'GET') {
      if (options.failList) return route.fulfill({status: 503, json: {detail: 'База данных недоступна'}});
      return route.fulfill({json: state.projects.map(summary)});
    }
    if (method === 'POST') {
      const data = route.request().postDataJSON() as {name: string; requirements: string};
      const project = makeProject(data.name, data.requirements);
      state.projects.unshift(project);
      return route.fulfill({status: 201, json: project});
    }
    return route.fallback();
  });

  await page.route(/\/api\/projects\/[^/]+\/jobs\/[^/]+$/, async route => {
    log(route);
    const step = steps[Math.min(polls, steps.length - 1)];
    polls += 1;
    const id = route.request().url().split('/').pop();
    return route.fulfill({
      json: {id, status: step.status, agent: 'analyst', subtype: step.subtype ?? null, result: step.result ?? null, num_turns: step.num_turns ?? null},
    });
  });

  await page.route(/\/api\/projects\/[^/]+\/jobs$/, async route => {
    log(route);
    const data = route.request().postDataJSON() as {agent: string};
    return route.fulfill({status: 202, json: {id: 'job-0001-abcdef', status: 'queued', agent: data.agent, subtype: null, result: null, num_turns: null}});
  });

  // Как backend/app/projects.py: тело — сам файл, имя — параметр name; формат проверяет сервер.
  const attachments = [...(options.attachments ?? [])];
  await page.route(/\/api\/projects\/[^/]+\/attachments(\?.*)?$/, async route => {
    const request = route.request();
    if (request.method() !== 'POST') return route.fulfill({json: attachments});
    const name = new URL(request.url()).searchParams.get('name') ?? '';
    const size = request.postDataBuffer()?.length ?? 0;
    state.requests.push({method: 'POST', url: request.url(), body: {name, size, type: request.headers()['content-type']}});
    if (!/^[\w.-]+\.(json|geojson|csv|txt|md|docx|pdf)$/i.test(name)) {
      return route.fulfill({status: 422, json: {detail: 'Имя файла: буквы, цифры, точка, дефис; форматы json, geojson, csv, txt, md, docx, pdf'}});
    }
    const saved = {name, size};
    attachments.splice(0, attachments.length, ...attachments.filter(file => file.name !== name), saved);
    return route.fulfill({status: 201, json: saved});
  });

  const runs = [...(options.runs ?? [])];
  await page.route(/\/api\/projects\/[^/]+\/runs$/, async route => {
    log(route);
    if (route.request().method() === 'POST') {
      const run = makeRun(route.request().url().split('/').at(-2) as string, []);
      runs.unshift(run);
      return route.fulfill({status: 201, json: run});
    }
    return route.fulfill({json: runs});
  });
  await page.route(/\/api\/runs\/[^/]+\/events\/stream$/, route => route.fulfill({status: 200, contentType: 'text/event-stream', body: ''}));
  await page.route(/\/api\/runs\/[^/]+\/artifacts$/, route =>
    route.fulfill({json: [{name: 'analysis', path: 'spec/analysis.json', stage: 'analysis', hash: 'x', size: 10, kind: 'json'}]}),
  );
  await page.route(/\/api\/runs\/[^/]+\/(stages\/[^/]+\/retry|answers|gates\/[^/]+\/decision|cancel)$/, async route => {
    log(route);
    return route.fulfill({status: 202, json: {status: 'accepted'}});
  });
  await page.route(/\/api\/runs\/[^/]+$/, route => {
    const run = runs.find(item => item['id'] === route.request().url().split('/').pop());
    return run ? route.fulfill({json: run}) : route.fulfill({status: 404, json: {detail: 'Прогон не найден'}});
  });

  await page.route(/\/api\/projects\/[^/]+$/, async route => {
    log(route);
    const id = route.request().url().split('/').pop();
    const project = state.projects.find(item => item.id === id);
    if (!project) return route.fulfill({status: 404, json: {detail: 'Проект не найден'}});
    if (route.request().method() === 'PATCH') {
      Object.assign(project, route.request().postDataJSON(), {updated_at: new Date().toISOString()});
    }
    return route.fulfill({json: project});
  });

  return state;
}

/** Прогон в форме `RunRead`: этапы — пары [ключ, статус] с необязательными воротами и текстом. */
export function makeRun(
  projectId: string,
  stages: {key: string; status: string; gate?: unknown; summary?: string; error?: string; attempt?: number}[],
  status = 'running',
  questions: unknown[] = [],
) {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    project_id: projectId,
    status,
    autonomy: 'A1',
    spec_version: 1,
    created_at: now,
    finished_at: null,
    budget: {tokens_used: 120000, tokens_limit: 1500000, minutes_used: 12, minutes_limit: 60},
    stages: stages.map(stage => ({
      title: stage.key,
      rwb_stage: '',
      participants: [],
      attempt: 1,
      started_at: now,
      finished_at: null,
      error: null,
      summary: null,
      gate: null,
      ...stage,
    })),
    flags: [],
    questions,
  };
}
