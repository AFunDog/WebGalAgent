import type { Task, TokenSummary } from '../types'
import { request } from './request'

export const tasksApi = {
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
  runStep: (id: string) => request<Task>(`/tasks/${id}/run-step`, { method: 'POST' }),
  updateTaskContent: (id: string, content: string) =>
    request<Task>(`/tasks/${id}/content`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),
  reviseStep: (id: string, stepIndex: number, instruction: string) =>
    request<Task>(`/tasks/${id}/steps/${stepIndex}/revise`, {
      method: 'POST',
      body: JSON.stringify({ instruction }),
    }),
  updateStepResult: (id: string, stepIndex: number, content: string) =>
    request<Task>(`/tasks/${id}/steps/${stepIndex}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),
  cancelTask: (id: string) => request<Task>(`/tasks/${id}/cancel`, { method: 'POST' }),
  getTokenSummary: () => request<TokenSummary>('/tasks/token-summary'),
}
