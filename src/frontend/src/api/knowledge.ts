import type { AgentKnowledgeRequirements, KnowledgeEntry } from '../types'
import { request } from './request'

export const knowledgeApi = {
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
  getAgentRequirements: () => request<AgentKnowledgeRequirements[]>('/knowledge/agent-requirements'),
  reloadKnowledge: () => request<{ status: string; count: string }>('/knowledge/reload', { method: 'POST' }),
}
