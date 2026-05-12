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
  messages: TaskMessage[]
  errors: string[]
  created_at: string
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
