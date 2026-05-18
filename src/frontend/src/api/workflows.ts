import type { AgentInfo, WorkflowInfo } from '../types'
import { request } from './request'

export const workflowApi = {
  getPipeline: () => request<WorkflowInfo>('/workflows/pipeline'),
  getAgentStatus: () => request<AgentInfo[]>('/workflows/agents/status'),
}
