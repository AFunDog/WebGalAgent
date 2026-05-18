import type { ProviderConfig, ProviderData, ProviderPresets } from '../types'
import { request } from './request'

export const providersApi = {
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
