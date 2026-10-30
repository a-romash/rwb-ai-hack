/** Агенты, которые есть в репозитории (`agents/<id>/`). Описания совпадают с их конфигурацией. */
export type AgentId = 'analyst' | 'developer';

export interface AgentInfo {
  id: AgentId;
  name: string;
  /** Винительный падеж для кнопок: «Запустить аналитика». */
  accusative: string;
  summary: string;
  icon: string;
}

export const AGENTS: Record<AgentId, AgentInfo> = {
  analyst: {
    id: 'analyst',
    name: 'Аналитик',
    accusative: 'аналитика',
    summary: 'Разбирает текст и отвечает структурированно, по схеме. Инструментов и доступа к коду нет.',
    icon: '@tui.sparkles',
  },
  developer: {
    id: 'developer',
    name: 'Разработчик',
    accusative: 'разработчика',
    summary: 'Читает и пишет код только в разрешённых каталогах, собирает проект и запускает тесты. Оболочки нет.',
    icon: '@tui.square-terminal',
  },
};

export const AGENT_LIST: readonly AgentInfo[] = [AGENTS.analyst, AGENTS.developer];

export function agentInfo(id: string | null | undefined): AgentInfo | null {
  return id && id in AGENTS ? AGENTS[id as AgentId] : null;
}
