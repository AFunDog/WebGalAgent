import type { LinkResponse, LinkStatus } from '../types'
import { request } from './request'

export const sceneLinkApi = {
  getLinkStatus: (linkPath?: string) =>
    request<LinkStatus>(`/scene-link/status${linkPath ? '?link_path=' + encodeURIComponent(linkPath) : ''}`),
  createLink: (taskId: string, linkPath?: string, force?: boolean) =>
    request<LinkResponse>('/scene-link/create', {
      method: 'POST',
      body: JSON.stringify({
        task_id: taskId,
        link_path: linkPath,
        force: force ?? false,
      }),
    }),
  removeLink: (linkPath?: string) =>
    request<LinkResponse>(`/scene-link/remove${linkPath ? '?link_path=' + encodeURIComponent(linkPath) : ''}`, {
      method: 'POST',
    }),
  resetLink: (linkPath?: string) =>
    request<LinkResponse>(`/scene-link/reset${linkPath ? '?link_path=' + encodeURIComponent(linkPath) : ''}`, {
      method: 'POST',
    }),
  listTasks: () => request<string[]>('/scene-link/tasks'),
}
