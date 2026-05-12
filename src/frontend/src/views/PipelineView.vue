<template>
  <div>
    <h2 class="page-title">流水线</h2>

    <!-- 流水线节点图（静态展示3个智能体） -->
    <PipelineGraph
      :agents="agentDefs"
      :messages="[]"
      active-agent=""
      :token-usage-by-step="activeTask?.token_usage_by_step"
      style="margin-bottom:24px"
    />

    <!-- 创建新任务 -->
    <div class="card">
      <div class="card-header"><h3>创建新任务</h3></div>
      <div class="form-group">
        <label>任务内容</label>
        <textarea
          v-model="newTaskContent"
          class="form-textarea"
          placeholder="请输入任务描述..."
          rows="4"
          @keyup.ctrl.enter="createTask"
        />
      </div>
      <div class="form-group">
        <label>起始步骤</label>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button
            v-for="(step, idx) in pipelineSteps"
            :key="step.name"
            class="btn btn-sm"
            :class="startStep === idx ? 'btn-primary' : ''"
            @click="setStartStep(idx)"
          >
            {{ String.fromCharCode(65 + idx) }}. {{ step.label }}
          </button>
        </div>
        <div v-if="startStep > 0" style="margin-top:4px;font-size:12px;color:var(--text-muted)">
          将跳过 {{ pipelineSteps.slice(0, startStep).map(s => s.label).join('、') }}，请提供 {{ requiredStepLabels }} 的内容
        </div>
      </div>
      <!-- 跳过步骤的输入框（只显示当前步骤依赖的前序步骤） -->
      <div v-for="depIdx in requiredPrevStepIndices" :key="'input-' + depIdx" class="form-group" style="margin-top:8px">
        <label>{{ pipelineSteps[depIdx]?.label }} 的输出内容</label>
        <textarea
          v-model="stepInputs[String(depIdx)]"
          class="form-textarea"
          :placeholder="'请输入 ' + pipelineSteps[depIdx]?.label + ' 的输出...'"
          rows="6"
          style="font-size:12px;font-family:monospace"
        />
      </div>
      <button class="btn btn-primary" :disabled="creating" @click="createTask">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px">
          <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        创建任务
      </button>
    </div>

    <!-- 当前任务逐步执行面板 -->
    <div v-if="activeTask" class="card" style="margin-top:24px">
      <div class="card-header">
        <h3>{{ activeTask.title || activeTask.content.slice(0, 40) }}</h3>
        <span class="badge" :class="statusBadgeClass(activeTask.status)">{{ statusLabel(activeTask.status) }}</span>
      </div>

      <!-- 步骤列表 -->
      <div class="step-list">
        <div
          v-for="(step, idx) in pipelineSteps"
          :key="step.name"
          class="step-item"
          :class="{
            'step-done': idx < activeTask.current_step,
            'step-active': idx === activeTask.current_step && activeTask.status !== 'completed',
            'step-pending': idx > activeTask.current_step || (idx === activeTask.current_step && activeTask.status === 'completed'),
          }"
        >
          <div class="step-header">
            <span class="step-index">{{ String.fromCharCode(65 + idx) }}</span>
            <span class="step-name">{{ step.label }}</span>
            <span class="step-status" :class="'step-status-' + getStepStatus(idx)">
              {{ getStepStatusText(idx) }}
            </span>
            <span v-if="getStepTokenUsage(idx)" class="step-token-badge">
              {{ formatTokenCount(getStepTokenUsage(idx)!.total_tokens) }} tokens
            </span>
          </div>

          <!-- 执行按钮 -->
          <button
            v-if="idx === activeTask.current_step && activeTask.status !== 'running' && activeTask.status !== 'completed'"
            class="btn btn-primary btn-sm"
            :disabled="runningStep"
            @click="runStep"
            style="margin-top:8px"
          >
            {{ runningStep ? '执行中...' : '执行此步骤' }}
          </button>

          <!-- 结果展示/编辑 -->
          <div v-if="idx < activeTask.current_step" class="step-result">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
              <span style="font-size:12px;color:var(--text-muted)">输出结果</span>
              <button
                v-if="editingStep !== idx"
                class="btn btn-sm"
                style="font-size:11px;padding:2px 8px"
                @click="startEdit(idx)"
              >编辑</button>
              <div v-else style="display:flex;gap:4px">
                <button class="btn btn-primary btn-sm" style="font-size:11px;padding:2px 8px" @click="saveEdit(idx)">保存</button>
                <button class="btn btn-sm" style="font-size:11px;padding:2px 8px" @click="cancelEdit">取消</button>
              </div>
            </div>
            <textarea
              v-if="editingStep === idx"
              v-model="editContent"
              class="form-textarea"
              rows="8"
              style="font-size:12px;font-family:monospace"
            />
            <pre v-else class="step-result-preview">{{ getStepResult(idx) }}</pre>
          </div>

          <!-- 运行中动画 -->
          <div v-if="idx === activeTask.current_step && activeTask.status === 'running'" class="step-running">
            <span class="pulse-dot"></span> 正在执行...
            <button class="btn btn-danger btn-sm" style="margin-left:8px" @click="cancelTask">终止</button>
          </div>
        </div>
      </div>

      <div style="margin-top:12px">
        <!-- Token 消耗汇总 -->
        <div v-if="activeTask.total_tokens > 0" class="token-summary-bar">
          <span class="token-summary-label">Token 消耗</span>
          <span class="token-summary-value">
            {{ formatTokenCount(activeTask.total_tokens) }}
            <span style="color:var(--text-muted);font-size:11px;margin-left:4px">
              (输入 {{ formatTokenCount(activeTask.total_prompt_tokens) }} / 输出 {{ formatTokenCount(activeTask.total_completion_tokens) }})
            </span>
          </span>
        </div>
        <router-link :to="{ name: 'tasks' }">查看所有任务历史</router-link>
      </div>
    </div>

    <!-- 无任务时的提示 -->
    <div v-else-if="!creating" class="empty-state" style="margin-top:16px">
      <p>创建任务后，可逐步执行每个智能体</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import PipelineGraph from '../components/PipelineGraph.vue'
import type { AgentInfo, Task } from '../types'

const agentDefs = ref<AgentInfo[]>([])
const newTaskContent = ref('')
const creating = ref(false)
const runningStep = ref(false)
const activeTask = ref<Task | null>(null)
const editingStep = ref<number | null>(null)
const editContent = ref('')
const startStep = ref(0)
const stepInputs = ref<Record<string, string>>({})

const pipelineSteps = [
  { name: 'outline_writer', label: '大纲编写', deps: [] as string[] },
  { name: 'script_writer', label: '剧本生成', deps: ['outline_writer'] },
  { name: 'script_converter', label: '脚本转换', deps: ['script_writer'] },
]

// 当前选择起始步骤时，需要填写输入的前序步骤索引列表
const requiredPrevStepIndices = computed(() => {
  if (startStep.value === 0) return []
  const step = pipelineSteps[startStep.value]
  if (!step) return []
  return step.deps
    .map(name => pipelineSteps.findIndex(s => s.name === name))
    .filter(idx => idx >= 0)
})

// 需要填写的步骤标签（用于提示文字）
const requiredStepLabels = computed(() =>
  requiredPrevStepIndices.value
    .map(idx => pipelineSteps[idx]?.label)
    .filter(Boolean)
    .join('、')
)

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'completed': return 'badge-success'
    case 'running': return 'badge-warning'
    case 'paused': return 'badge-info'
    case 'failed': return 'badge-danger'
    case 'cancelled': return 'badge-danger'
    default: return 'badge-muted'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'completed': return '已完成'
    case 'running': return '执行中'
    case 'paused': return '等待下一步'
    case 'pending': return '待开始'
    case 'failed': return '失败'
    case 'cancelled': return '已取消'
    default: return status
  }
}

function getStepStatus(idx: number): string {
  if (!activeTask.value) return 'pending'
  if (idx < activeTask.value.current_step) return 'done'
  if (idx === activeTask.value.current_step) {
    if (activeTask.value.status === 'running') return 'running'
    if (activeTask.value.status === 'completed') return 'done'
    return 'ready'
  }
  return 'pending'
}

function getStepStatusText(idx: number): string {
  const s = getStepStatus(idx)
  switch (s) {
    case 'done': return '已完成'
    case 'running': return '执行中'
    case 'ready': return '待执行'
    default: return '等待中'
  }
}

function getStepResult(idx: number): string {
  if (!activeTask.value) return ''
  return activeTask.value.step_results[String(idx)] || ''
}

function getStepTokenUsage(idx: number): { prompt_tokens: number; completion_tokens: number; total_tokens: number } | null {
  if (!activeTask.value) return null
  return activeTask.value.token_usage_by_step?.[String(idx)] ?? null
}

function formatTokenCount(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

function startEdit(idx: number) {
  editingStep.value = idx
  editContent.value = getStepResult(idx)
}

function cancelEdit() {
  editingStep.value = null
  editContent.value = ''
}

async function saveEdit(idx: number) {
  if (!activeTask.value) return
  try {
    const updated = await api.updateStepResult(activeTask.value.id, idx, editContent.value)
    activeTask.value = updated
    editingStep.value = null
    editContent.value = ''
  } catch (e) {
    alert('保存失败: ' + (e instanceof Error ? e.message : String(e)))
  }
}

async function createTask() {
  const content = newTaskContent.value.trim()
  if (!content) return
  // 检查依赖步骤的输入是否都已填写
  if (startStep.value > 0) {
    for (const idx of requiredPrevStepIndices.value) {
      if (!stepInputs.value[String(idx)]?.trim()) {
        alert(`请填写「${pipelineSteps[idx]?.label}」的输出内容`)
        return
      }
    }
  }
  creating.value = true
  try {
    const task = await api.createTask(content, {
      startStep: startStep.value,
      stepInputs: startStep.value > 0 ? stepInputs.value : undefined,
    })
    newTaskContent.value = ''
    startStep.value = 0
    stepInputs.value = {}
    activeTask.value = task
  } catch (e) {
    alert('创建任务失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    creating.value = false
  }
}

function setStartStep(idx: number) {
  startStep.value = idx
  // 只保留依赖步骤的输入
  const newInputs: Record<string, string> = {}
  if (idx > 0) {
    const step = pipelineSteps[idx]
    if (step) {
      for (const depName of step.deps) {
        const depIdx = pipelineSteps.findIndex(s => s.name === depName)
        if (depIdx >= 0) {
          newInputs[String(depIdx)] = stepInputs.value[String(depIdx)] || ''
        }
      }
    }
  }
  stepInputs.value = newInputs
}

async function runStep() {
  if (!activeTask.value) return
  runningStep.value = true
  try {
    const updated = await api.runStep(activeTask.value.id)
    activeTask.value = updated
    // 如果正在运行，开始轮询
    if (updated.status === 'running') {
      pollTask(updated.id)
    }
  } catch (e) {
    alert('执行步骤失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    runningStep.value = false
  }
}

async function cancelTask() {
  if (!activeTask.value) return
  try {
    const updated = await api.cancelTask(activeTask.value.id)
    activeTask.value = updated
  } catch (e) {
    alert('终止任务失败: ' + (e instanceof Error ? e.message : String(e)))
  }
}

function pollTask(taskId: string) {
  const poll = async () => {
    try {
      const task = await api.getTask(taskId)
      activeTask.value = task
      if (task.status === 'running') {
        setTimeout(poll, 1500)
      }
    } catch (e) {
      console.error('轮询失败:', e)
    }
  }
  setTimeout(poll, 1500)
}

onMounted(async () => {
  try {
    const info = await api.getPipeline()
    agentDefs.value = info.agents
  } catch (e) {
    console.error('Failed to load pipeline info:', e)
  }
  // 如果有最近的任务，加载它
  try {
    const tasks = await api.getTasks()
    const lastTask = tasks[tasks.length - 1]
    if (lastTask && (lastTask.status === 'pending' || lastTask.status === 'paused' || lastTask.status === 'running')) {
      activeTask.value = lastTask
      if (lastTask.status === 'running') {
        pollTask(lastTask.id)
      }
    }
  } catch {
    // ignore
  }
})
</script>

<style scoped>
.step-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.step-item {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 16px;
  transition: border-color 0.2s;
}
.step-item.step-active {
  border-color: var(--primary-hover);
  background: rgba(99,102,241,0.04);
}
.step-item.step-done {
  border-color: var(--success);
  background: rgba(34,197,94,0.03);
}
.step-header {
  display: flex;
  align-items: center;
  gap: 10px;
}
.step-index {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  background: var(--border);
}
.step-active .step-index { background: var(--primary-hover); }
.step-done .step-index { background: var(--success); }
.step-name {
  font-weight: 600;
  font-size: 14px;
}
.step-status {
  margin-left: auto;
  font-size: 12px;
  font-weight: 500;
}
.step-status-done { color: var(--success); }
.step-status-running { color: var(--primary-hover); }
.step-status-ready { color: var(--warning); }
.step-status-pending { color: var(--text-muted); }
.step-result {
  margin-top: 8px;
}
.step-result-preview {
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px;
  font-size: 12px;
  font-family: monospace;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}
.step-running {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  color: var(--primary-hover);
  font-size: 13px;
}
.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary-hover);
  animation: pulse 1.2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.badge-info {
  background: rgba(99,102,241,0.12);
  color: var(--primary-hover);
}
.step-token-badge {
  margin-left: 8px;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(245,158,11,0.12);
  color: #d97706;
}
.token-summary-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(245,158,11,0.06);
  border: 1px solid rgba(245,158,11,0.2);
  border-radius: var(--radius);
  margin-bottom: 12px;
}
.token-summary-label {
  font-size: 12px;
  font-weight: 600;
  color: #d97706;
}
.token-summary-value {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}
</style>
