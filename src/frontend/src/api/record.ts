import type { RecordConfig, RecordResult } from '../types'
import { request } from './request'

export const recordApi = {
  startRecord: (config: RecordConfig) =>
    request<RecordResult>('/record/start', {
      method: 'POST',
      body: JSON.stringify(config),
    }),
  stopRecord: () => request<RecordResult>('/record/stop', { method: 'POST' }),
  getRecordStatus: () =>
    request<{
      recording: boolean
      progress?: number
      logs?: string[]
      success?: boolean
      message?: string
      output_path?: string | null
      total_frames?: number
      duration?: number
      source_fps?: number
      output_fps?: number
      file_size_mb?: number
      has_audio?: boolean
    }>('/record/status'),
  getRecordConfig: () => request<RecordConfig>('/record/config'),
}
