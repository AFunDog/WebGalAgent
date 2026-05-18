<template>
  <div class="pipeline-graph">
    <svg :width="svgWidth" :height="svgHeight" :viewBox="`0 0 ${svgWidth} ${svgHeight}`">
      <!-- 连线层：表达步骤间的数据流与当前激活链路 -->
      <template v-for="(edge, i) in edges" :key="'e' + i">
        <line
          :x1="edge.x1" :y1="edge.y1"
          :x2="edge.x2" :y2="edge.y2"
          :stroke="edge.active ? 'var(--primary-hover)' : 'var(--border)'"
          :stroke-width="edge.active ? 2.5 : 1.5"
          :stroke-dasharray="edge.active ? '8,4' : 'none'"
        />
        <!-- 箭头 -->
        <polygon
          :points="arrowPoints(edge.x2, edge.y2, edge.x1, edge.y1)"
          :fill="edge.active ? 'var(--primary-hover)' : 'var(--border)'"
        />
        <!-- 数据标签 -->
        <text
          :x="(edge.x1 + edge.x2) / 2"
          :y="(edge.y1 + edge.y2) / 2 - 8"
          text-anchor="middle"
          fill="var(--text-muted)"
          font-size="11"
        >{{ edge.label }}</text>
      </template>

      <!-- 节点层：展示每个 agent 的名称、状态、输入输出摘要与 token 消耗 -->
      <g v-for="(node, i) in nodes" :key="'n' + i" :transform="`translate(${node.x}, ${node.y})`">
        <!-- 背景框 -->
        <rect
          :width="nodeW" :height="nodeH" :rx="8"
          :fill="nodeFill(node)"
          :stroke="nodeStroke(node)"
          :stroke-width="node.status === 'running' ? 2 : 1"
        />
        <!-- 运行中脉冲动画 -->
        <rect
          v-if="node.status === 'running'"
          :width="nodeW" :height="nodeH" :rx="8"
          fill="none"
          stroke="var(--primary-hover)"
          stroke-width="2"
          opacity="0.6"
        >
          <animate attributeName="opacity" values="0.6;0.1;0.6" dur="1.5s" repeatCount="indefinite" />
        </rect>

        <!-- 步骤标签 -->
        <text
          :x="12" :y="22"
          fill="var(--text-muted)" font-size="10" font-weight="600"
        >{{ node.stepLabel }}</text>

        <!-- 名称 -->
        <text
          :x="12" :y="40"
          fill="var(--text)" font-size="13" font-weight="700"
        >{{ node.label }}</text>

        <!-- 状态 -->
        <text
          :x="12" :y="56"
          :fill="statusColor(node.status)" font-size="11" font-weight="500"
        >{{ statusText(node.status) }}</text>

        <!-- 模型 -->
        <text
          :x="nodeW - 12" :y="22"
          text-anchor="end"
          fill="var(--text-muted)" font-size="10"
        >{{ node.model }}</text>

        <!-- 输入/输出预览 -->
        <text
          v-if="node.inputPreview"
          :x="12" :y="72"
          fill="var(--text-muted)" font-size="10"
        >📥 {{ node.inputPreview }}</text>
        <text
          v-if="node.outputPreview"
          :x="12" :y="86"
          fill="var(--text-muted)" font-size="10"
        >📤 {{ node.outputPreview }}</text>

        <!-- Token 消耗 -->
        <text
          v-if="node.tokenUsage > 0"
          :x="nodeW - 12" :y="56"
          text-anchor="end"
          fill="#d97706" font-size="10" font-weight="500"
        >⚡{{ formatTokenCount(node.tokenUsage) }}</text>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AgentInfo, TaskMessage } from '../types'

const props = defineProps<{
  agents: AgentInfo[]
  messages: TaskMessage[]
  activeAgent: string
  tokenUsageByStep?: Record<string, { prompt_tokens: number; completion_tokens: number; total_tokens: number }>
}>()

// 图结构保持固定三步，页面只传运行时状态与消息摘要。
const AGENT_LABELS: Record<string, string> = {
  outline_writer: '大纲编写',
  script_writer: '剧本生成',
  script_converter: '脚本转换',
}
const STEP_LABELS = ['A', 'B', 'C']
const AGENT_ORDER = ['outline_writer', 'script_writer', 'script_converter']

const nodeW = 180
const nodeH = 96
const gapX = 60
const gapY = 40
const paddingX = 20
const paddingY = 20

interface PipelineNode {
  name: string
  label: string
  stepLabel: string
  model: string
  x: number
  y: number
  status: 'idle' | 'running' | 'done' | 'error'
  inputPreview: string
  outputPreview: string
  tokenUsage: number
}

interface PipelineEdge {
  x1: number
  y1: number
  x2: number
  y2: number
  label: string
  active: boolean
}

// 节点状态优先从 result 消息推断，其次才回退到 activeAgent 和前序完成情况。
function getNodeStatus(name: string): PipelineNode['status'] {
  const resultMsg = props.messages.find(m => m.type === 'result' && m.sender === name)
  if (resultMsg) {
    // 检查是否有错误
    const tc = resultMsg.metadata?.tool_calls as Array<{ success: boolean }> | undefined
    if (tc && tc.some(t => !t.success)) return 'error'
    return 'done'
  }
  if (props.activeAgent === name) return 'running'
  // 如果前一个节点完成了，这个节点应该运行中或已完成
  const idx = AGENT_ORDER.indexOf(name)
  if (idx > 0) {
    const prevResult = props.messages.find(m => m.type === 'result' && m.sender === AGENT_ORDER[idx - 1])
    if (prevResult && !resultMsg) return 'running'
  }
  return 'idle'
}

function getPreview(content: string, maxLen = 20): string {
  const first = content.split('\n').find(l => l.trim()) ?? ''
  if (first.length <= maxLen) return first
  return first.slice(0, maxLen) + '…'
}

// 输入/输出摘要只取首个非空行，避免图节点被长文本撑破。
function getInputPreview(name: string): string {
  const taskMsg = props.messages.find(m => m.type === 'task' && m.receiver === name)
  if (taskMsg) return getPreview(taskMsg.content)
  // 对于 B 和 C，输入是前一个节点的输出
  const idx = AGENT_ORDER.indexOf(name)
  if (idx > 0) {
    const prevResult = props.messages.find(m => m.type === 'result' && m.sender === AGENT_ORDER[idx - 1])
    if (prevResult) return getPreview(prevResult.content)
  }
  return ''
}

function getOutputPreview(name: string): string {
  const resultMsg = props.messages.find(m => m.type === 'result' && m.sender === name)
  if (resultMsg) return getPreview(resultMsg.content)
  return ''
}

const nodes = computed<PipelineNode[]>(() => {
  const agentNames = AGENT_ORDER
  const cols = 3
  return agentNames.map((name, i) => {
    const col = i % cols
    const row = Math.floor(i / cols)
    const agent = props.agents.find(a => a.name === name)
    return {
      name,
      label: AGENT_LABELS[name] ?? name,
      stepLabel: STEP_LABELS[i] ?? String(i + 1),
      model: agent?.model ?? '',
      x: paddingX + col * (nodeW + gapX),
      y: paddingY + row * (nodeH + gapY),
      status: getNodeStatus(name),
      inputPreview: getInputPreview(name),
      outputPreview: getOutputPreview(name),
      tokenUsage: props.tokenUsageByStep?.[String(i)]?.total_tokens ?? 0,
    }
  })
})

// 边的高亮语义是“上一步已完成，且下一步已进入运行或完成状态”。
const edges = computed<PipelineEdge[]>(() => {
  const result: PipelineEdge[] = []
  const edgeLabels = ['大纲', '剧本']
  for (let i = 0; i < nodes.value.length - 1; i++) {
    const from = nodes.value[i]!
    const to = nodes.value[i + 1]!
    const isActive = from.status === 'done' && (to.status === 'running' || to.status === 'done')
    result.push({
      x1: from.x + nodeW,
      y1: from.y + nodeH / 2,
      x2: to.x,
      y2: to.y + nodeH / 2,
      label: edgeLabels[i] ?? '',
      active: isActive,
    })
  }
  return result
})

const svgWidth = computed(() => paddingX * 2 + 3 * nodeW + 2 * gapX)
const svgHeight = computed(() => paddingY * 2 + nodeH)

function arrowPoints(tipX: number, tipY: number, fromX: number, fromY: number): string {
  const size = 6
  const dx = tipX - fromX
  const dy = tipY - fromY
  const len = Math.sqrt(dx * dx + dy * dy) || 1
  const ux = dx / len
  const uy = dy / len
  const px = tipX - ux * size
  const py = tipY - uy * size
  const nx = -uy * size * 0.5
  const ny = ux * size * 0.5
  return `${tipX},${tipY} ${px + nx},${py + ny} ${px - nx},${py - ny}`
}

function nodeFill(node: PipelineNode): string {
  switch (node.status) {
    case 'running': return 'rgba(99,102,241,0.12)'
    case 'done': return 'rgba(34,197,94,0.08)'
    case 'error': return 'rgba(239,68,68,0.08)'
    default: return 'var(--bg-input)'
  }
}

function nodeStroke(node: PipelineNode): string {
  switch (node.status) {
    case 'running': return 'var(--primary-hover)'
    case 'done': return 'var(--success)'
    case 'error': return 'var(--danger)'
    default: return 'var(--border)'
  }
}

function statusColor(status: PipelineNode['status']): string {
  switch (status) {
    case 'running': return 'var(--primary-hover)'
    case 'done': return 'var(--success)'
    case 'error': return 'var(--danger)'
    default: return 'var(--text-muted)'
  }
}

function statusText(status: PipelineNode['status']): string {
  switch (status) {
    case 'running': return '运行中...'
    case 'done': return '已完成'
    case 'error': return '出错'
    default: return '等待中'
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
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px;
  overflow-x: auto;
}
.pipeline-graph text {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  user-select: none;
}
</style>
