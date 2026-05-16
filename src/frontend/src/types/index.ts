// ===== 知识库 =====

export interface KnowledgeEntry {
  id: string
  category: string
  title: string
  tags: string[]
  body: string
  source: string
  created_at: string
  updated_at: string
}

export interface AgentKnowledgeRequirements {
  agent: string
  categories: string[]
  tags: string[]
}

// ===== 工作流 =====

export interface AgentInfo {
  name: string
  description: string
  state: string
  provider: string
  model: string
}

export interface WorkflowInfo {
  name: string
  agents: AgentInfo[]
  type: string
  description: string
}

// ===== 任务 =====

export interface ToolCallRecord {
  tool: string
  args: Record<string, unknown>
  success: boolean
  result: unknown
}

export interface TaskMessage {
  id: string
  type: string
  sender: string
  receiver: string
  content: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface Task {
  id: string
  status: string
  workflow: string
  content: string
  title: string
  current_step: number
  step_results: Record<string, string>
  messages: TaskMessage[]
  errors: string[]
  created_at: string
  token_usage_by_step: Record<string, { prompt_tokens: number; completion_tokens: number; total_tokens: number }>
  total_prompt_tokens: number
  total_completion_tokens: number
  total_tokens: number
}

// ===== Token 统计 =====

export interface TokenSummary {
  total_tasks: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_tokens: number
  by_step: Record<string, { prompt_tokens: number; completion_tokens: number; total_tokens: number }>
}

// ===== 提供商 =====

export interface ProviderConfig {
  provider: string
  model: string
  base_url: string
  api_key: string
  temperature: number
  max_tokens: number
}

export interface ProviderData {
  defaults: ProviderConfig
  agents: Record<string, ProviderConfig>
}

export interface ProviderPresets {
  [key: string]: {
    provider?: string
    base_url?: string
    [key: string]: unknown
  }
}

// ===== 软链接 =====

export interface LinkResponse {
  success: boolean
  message: string
  link_path: string | null
  target_path: string | null
}

export interface LinkStatus {
  path: string
  exists: boolean
  is_symlink: boolean
  target: string | null
  valid: boolean
}

// ===== 录制 =====

export interface RecordConfig {
  url: string
  output_path: string
  duration: number
  fps: number
  canvas_selector: string
}

export interface RecordResult {
  success: boolean
  message: string
  output_path: string | null
  total_frames: number
  duration: number
  file_size_mb: number
}
