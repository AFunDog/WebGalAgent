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
  createTask: (content: string, options?: { startStep?: number; stepInputs?: Record<string, string> }) =>
    request<Task>('/tasks', {
      method: 'POST',
      body: JSON.stringify({
        content,
        start_step: options?.startStep ?? 0,
        step_inputs: options?.stepInputs ?? {},
      }),
    }),
  getTask: (id: string) => request<Task>(`/tasks/${id}`),
  runStep: (id: string) =>
    request<Task>(`/tasks/${id}/run-step`, { method: 'POST' }),
  updateStepResult: (id: string, stepIndex: number, content: string) =>
    request<Task>(`/tasks/${id}/steps/${stepIndex}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),
  cancelTask: (id: string) =>
    request<Task>(`/tasks/${id}/cancel`, { method: 'POST' }),

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
