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
  updateStepResult: (id: string, stepIndex: number, content: string) =>
    request<Task>(`/tasks/${id}/steps/${stepIndex}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),
  cancelTask: (id: string) => request<Task>(`/tasks/${id}/cancel`, { method: 'POST' }),
  getTokenSummary: () => request<TokenSummary>('/tasks/token-summary'),
}
