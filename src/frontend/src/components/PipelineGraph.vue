<template>
  <div class="pipeline-graph">
    <button
      v-for="(node, index) in nodes"
      :key="node.name"
      class="pipeline-node"
      :class="[
        `pipeline-node--${node.status}`,
        { 'pipeline-node--selected': selectedNode === node.name },
      ]"
      type="button"
      @click="$emit('select-node', node.name)"
    >
      <div class="pipeline-node__topline">
        <span class="pipeline-node__step">{{ node.stepLabel }}</span>
        <span v-if="node.tokenUsage > 0" class="pipeline-node__token">
          {{ formatTokenCount(node.tokenUsage) }}
        </span>
      </div>
      <div class="pipeline-node__title">{{ node.label }}</div>
      <div class="pipeline-node__status">
        <span class="pipeline-node__dot"></span>
        {{ statusText(node.status) }}
      </div>
      <div class="pipeline-node__model">{{ node.model || '未配置模型' }}</div>
      <div class="pipeline-node__preview">
        <div class="pipeline-node__preview-line">
          <span class="pipeline-node__preview-label">IN</span>
          <span>{{ node.inputPreview || '等待输入' }}</span>
        </div>
        <div class="pipeline-node__preview-line">
          <span class="pipeline-node__preview-label">OUT</span>
          <span>{{ node.outputPreview || '尚无输出' }}</span>
        </div>
      </div>
      <div class="pipeline-node__capabilities">
        <span class="pipeline-node__meta-chip">知识 {{ node.knowledgeCount }}</span>
        <span class="pipeline-node__meta-chip">工具 {{ node.toolCount }}</span>
      </div>
      <div v-if="index < nodes.length - 1" class="pipeline-node__connector" aria-hidden="true">
        <span class="pipeline-node__connector-line"></span>
        <span class="pipeline-node__connector-head"></span>
      </div>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AgentInfo, AgentKnowledgeRequirements, TaskMessage } from '../types'

const props = defineProps<{
  agents: AgentInfo[]
  knowledgeRequirements?: AgentKnowledgeRequirements[]
  messages: TaskMessage[]
  activeAgent: string
  selectedNode?: string
  tokenUsageByStep?: Record<string, { prompt_tokens: number; completion_tokens: number; total_tokens: number }>
}>()

defineEmits<{
  (e: 'select-node', nodeName: string): void
}>()

const AGENT_LABELS: Record<string, string> = {
  outline_writer: '大纲编写',
  script_writer: '剧本生成',
  script_converter: '脚本转换',
}

const STEP_LABELS = ['A', 'B', 'C']
const AGENT_ORDER = ['outline_writer', 'script_writer', 'script_converter']

interface PipelineNode {
  name: string
  label: string
  stepLabel: string
  model: string
  status: 'idle' | 'running' | 'done' | 'error'
  inputPreview: string
  outputPreview: string
  tokenUsage: number
  knowledgeCount: number
  toolCount: number
}

function findLastMessage(predicate: (message: TaskMessage) => boolean): TaskMessage | undefined {
  for (let i = props.messages.length - 1; i >= 0; i -= 1) {
    const message = props.messages[i]
    if (message && predicate(message)) return message
  }
  return undefined
}

function getNodeStatus(name: string): PipelineNode['status'] {
  const resultMsg = findLastMessage(m => m.type === 'result' && m.sender === name)
  if (resultMsg) {
    const toolCalls = resultMsg.metadata?.tool_calls as Array<{ success: boolean }> | undefined
    if (toolCalls && toolCalls.some(call => !call.success)) return 'error'
    return 'done'
  }
  if (props.activeAgent === name) return 'running'
  const idx = AGENT_ORDER.indexOf(name)
  if (idx > 0) {
    const prevResult = findLastMessage(
      m => m.type === 'result' && m.sender === AGENT_ORDER[idx - 1],
    )
    if (prevResult) return 'running'
  }
  return 'idle'
}

function getPreview(content: string, maxLen = 28): string {
  const first = content.split('\n').find(line => line.trim()) ?? ''
  if (first.length <= maxLen) return first
  return first.slice(0, maxLen) + '…'
}

function getInputPreview(name: string): string {
  const taskMsg = findLastMessage(m => m.type === 'task' && m.receiver === name)
  if (taskMsg) return getPreview(taskMsg.content)
  const idx = AGENT_ORDER.indexOf(name)
  if (idx > 0) {
    const prevResult = findLastMessage(
      m => m.type === 'result' && m.sender === AGENT_ORDER[idx - 1],
    )
    if (prevResult) return getPreview(prevResult.content)
  }
  return ''
}

function getOutputPreview(name: string): string {
  const resultMsg = findLastMessage(m => m.type === 'result' && m.sender === name)
  return resultMsg ? getPreview(resultMsg.content) : ''
}

const nodes = computed<PipelineNode[]>(() =>
  AGENT_ORDER.map((name, index) => {
    const agent = props.agents.find(item => item.name === name)
    const requirement = props.knowledgeRequirements?.find(item => item.agent === name)
    return {
      name,
      label: AGENT_LABELS[name] ?? name,
      stepLabel: STEP_LABELS[index] ?? String(index + 1),
      model: agent?.model ?? '',
      status: getNodeStatus(name),
      inputPreview: getInputPreview(name),
      outputPreview: getOutputPreview(name),
      tokenUsage: props.tokenUsageByStep?.[String(index)]?.total_tokens ?? 0,
      knowledgeCount: (requirement?.categories.length ?? 0) + (requirement?.tags.length ?? 0),
      toolCount: agent?.tools.length ?? 0,
    }
  }),
)

function statusText(status: PipelineNode['status']): string {
  switch (status) {
    case 'running': return '运行中'
    case 'done': return '已完成'
    case 'error': return '异常'
    default: return '待执行'
  }
}

function formatTokenCount(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}
</script>

<style scoped>
.pipeline-graph {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.pipeline-node {
  position: relative;
  text-align: left;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(28, 28, 28, 0.96), rgba(18, 18, 18, 0.98));
  padding: 14px;
  min-height: 172px;
  color: var(--text);
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.pipeline-node:hover {
  transform: translateY(-2px);
  border-color: var(--border-strong);
}

.pipeline-node--selected {
  border-color: rgba(247, 99, 12, 0.42);
  box-shadow: 0 0 0 3px rgba(247, 99, 12, 0.12);
}

.pipeline-node--running {
  border-color: rgba(247, 99, 12, 0.32);
  background: linear-gradient(180deg, rgba(247, 99, 12, 0.12), rgba(18, 18, 18, 0.98));
}

.pipeline-node--done {
  border-color: rgba(93, 211, 158, 0.24);
}

.pipeline-node--error {
  border-color: rgba(255, 107, 87, 0.26);
}

.pipeline-node__topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.pipeline-node__step {
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--text-muted);
  font-weight: 700;
}

.pipeline-node__token {
  font-size: 10px;
  color: #ffb488;
  background: rgba(247, 99, 12, 0.12);
  border: 1px solid rgba(247, 99, 12, 0.18);
  border-radius: 999px;
  padding: 2px 7px;
}

.pipeline-node__title {
  font-size: 16px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.pipeline-node__status {
  margin-top: 6px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-soft);
}

.pipeline-node__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
}

.pipeline-node--running .pipeline-node__dot {
  background: var(--primary-hover);
  box-shadow: 0 0 0 4px rgba(247, 99, 12, 0.16);
}

.pipeline-node--done .pipeline-node__dot {
  background: var(--success);
}

.pipeline-node--error .pipeline-node__dot {
  background: var(--danger);
}

.pipeline-node__model {
  margin-top: 10px;
  color: var(--text-muted);
  font-size: 11px;
}

.pipeline-node__preview {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pipeline-node__capabilities {
  margin-top: 14px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.pipeline-node__meta-chip {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.pipeline-node__preview-line {
  display: grid;
  grid-template-columns: 26px 1fr;
  gap: 8px;
  font-size: 11px;
  color: var(--text-soft);
  line-height: 1.45;
}

.pipeline-node__preview-label {
  color: var(--text-muted);
  font-weight: 700;
}

.pipeline-node__connector {
  position: absolute;
  top: 50%;
  right: -18px;
  width: 18px;
  height: 14px;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
}

.pipeline-node__connector-line {
  flex: 1;
  height: 1px;
  background: var(--border-strong);
}

.pipeline-node__connector-head {
  width: 6px;
  height: 6px;
  border-top: 1px solid var(--border-strong);
  border-right: 1px solid var(--border-strong);
  transform: rotate(45deg);
  margin-left: -1px;
}

@media (max-width: 1080px) {
  .pipeline-graph {
    grid-template-columns: 1fr;
  }

  .pipeline-node {
    min-height: auto;
  }

  .pipeline-node__connector {
    display: none;
  }
}
</style>
