import type {
  KnowledgeEntry,
  AgentKnowledgeRequirements,
  WorkflowInfo,
  AgentInfo,
  Task,
  ProviderData,
  ProviderPresets,
  ProviderConfig,
} from '../types'

const BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(BASE + url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`${response.status}: ${await response.text()}`)
  }
  return response.json()
}

export const api = {
  // ----- 知识库 -----
  getKnowledge(params?: {
    category?: string
    keyword?: string
    tags?: string[]
  }): Promise<KnowledgeEntry[]> {
    const qs = new URLSearchParams()
    if (params?.category) qs.set('category', params.category)
    if (params?.keyword) qs.set('keyword', params.keyword)
    if (params?.tags?.length) qs.set('tags', params.tags.join(','))
    const query = qs.toString()
    return request<KnowledgeEntry[]>(`/knowledge${query ? '?' + query : ''}`)
  },

  getCategories: () => request<string[]>('/knowledge/categories'),
  getTags: () => request<string[]>('/knowledge/tags'),
  getAgentRequirements: () =>
    request<AgentKnowledgeRequirements[]>('/knowledge/agent-requirements'),
  reloadKnowledge: () =>
    request<{ status: string; count: string }>('/knowledge/reload', {
      method: 'POST',
    }),

  // ----- 工作流 -----
  getPipeline: () => request<WorkflowInfo>('/workflows/pipeline'),
  getAgentStatus: () => request<AgentInfo[]>('/workflows/agents/status'),

  // ----- 任务 -----
  getTasks: () => request<Task[]>('/tasks'),
  createTask: (content: string) =>
    request<Task>('/tasks', {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
  getTask: (id: string) => request<Task>(`/tasks/${id}`),

  // ----- 提供商 -----
  getProviders: () => request<ProviderData>('/providers'),
  getPresets: () => request<ProviderPresets>('/providers/presets'),
  saveDefaultProvider: (config: ProviderConfig) =>
    request<{ ok: boolean }>('/providers', {
      method: 'PUT',
      body: JSON.stringify(config),
    }),
  saveAgentProvider: (agentName: string, config: ProviderConfig) =>
    request<{ ok: boolean; agent: string }>(`/providers/${agentName}`, {
      method: 'PUT',
      body: JSON.stringify(config),
    }),
}
