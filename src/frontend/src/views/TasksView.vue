<template>
  <div>
    <h2 class="page-title">任务历史</h2>

    <!-- 全局 Token 统计卡片 -->
    <div v-if="tokenSummary && tokenSummary.total_tokens > 0" class="card" style="margin-bottom:16px">
      <div class="card-header"><h3>Token 消耗统计</h3></div>
      <div class="token-stats-grid">
        <div class="token-stat-item">
          <div class="token-stat-value">{{ formatTokenCount(tokenSummary.total_tokens) }}</div>
          <div class="token-stat-label">总消耗</div>
        </div>
        <div class="token-stat-item">
          <div class="token-stat-value">{{ formatTokenCount(tokenSummary.total_prompt_tokens) }}</div>
          <div class="token-stat-label">输入</div>
        </div>
        <div class="token-stat-item">
          <div class="token-stat-value">{{ formatTokenCount(tokenSummary.total_completion_tokens) }}</div>
          <div class="token-stat-label">输出</div>
        </div>
        <div class="token-stat-item">
          <div class="token-stat-value">{{ tokenSummary.total_tasks }}</div>
          <div class="token-stat-label">任务数</div>
        </div>
      </div>
      <div v-if="Object.keys(tokenSummary.by_step).length > 0" class="token-by-step">
        <span v-for="(usage, name) in tokenSummary.by_step" :key="name" class="token-step-badge">
          {{ agentLabel(name) }}: {{ formatTokenCount(usage.total_tokens) }}
        </span>
      </div>
    </div>

    <div v-if="tasks.length === 0" class="empty-state">
      <p>暂无任务，前往<router-link :to="{ name: 'pipeline' }">流水线</router-link>创建新任务</p>
    </div>

    <div v-for="task in reversedTasks" :key="task.id" class="card" style="margin-bottom:16px">
      <div class="card-header">
        <h3>{{ task.title || task.content.slice(0, 60) }}</h3>
        <div style="display:flex;gap:8px;align-items:center">
          <span class="badge" :class="statusBadgeClass(task.status)">{{ statusLabel(task.status) }}</span>
        </div>
      </div>
      <p style="color:var(--text-muted);font-size:12px">
        ID: {{ task.id }} · {{ formatTime(task.created_at) }} · 步骤: {{ task.current_step }}/{{ pipelineSteps.length }}
        <span v-if="task.total_tokens > 0" style="margin-left:8px;color:#d97706">
          · {{ formatTokenCount(task.total_tokens) }} tokens
        </span>
      </p>
      <p
        v-if="task.errors.length"
        style="color:var(--danger);font-size:12px;margin-top:4px"
      >{{ task.errors.join('; ') }}</p>

      <!-- 步骤列表 -->
      <div class="step-list" style="margin-top:12px">
        <div
          v-for="(step, idx) in pipelineSteps"
          :key="step.name"
          class="step-item"
          :class="{
            'step-done': idx < task.current_step,
            'step-active': idx === task.current_step && task.status !== 'completed',
            'step-pending': idx > task.current_step,
          }"
        >
          <div class="step-header">
            <span class="step-index">{{ String.fromCharCode(65 + idx) }}</span>
            <span class="step-name">{{ step.label }}</span>
            <span class="step-status" :class="'step-status-' + getStepStatus(task, idx)">
              {{ getStepStatusText(task, idx) }}
            </span>
            <span v-if="task.token_usage_by_step?.[String(idx)]" class="step-token-badge">
              {{ formatTokenCount(task.token_usage_by_step?.[String(idx)]?.total_tokens ?? 0) }} tokens
            </span>
          </div>

          <!-- 执行按钮（仅在当前步骤且非运行中时显示） -->
          <button
            v-if="idx === task.current_step && task.status !== 'running' && task.status !== 'completed'"
            class="btn btn-primary btn-sm"
            :disabled="runningTasks.has(task.id)"
            @click="runStep(task.id)"
            style="margin-top:8px"
          >
            {{ runningTasks.has(task.id) ? '执行中...' : '执行此步骤' }}
          </button>

          <!-- 结果展示/编辑 -->
          <div v-if="idx < task.current_step" class="step-result">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
              <span style="font-size:12px;color:var(--text-muted)">输出结果</span>
              <div style="display:flex;gap:4px">
                <button
                  v-if="editingKey !== `${task.id}-${idx}`"
                  class="btn btn-sm"
                  style="font-size:11px;padding:2px 8px"
                  @click="startEdit(task.id, idx, getStepResult(task, idx))"
                >编辑</button>
                <template v-else>
                  <button class="btn btn-primary btn-sm" style="font-size:11px;padding:2px 8px" @click="saveEdit(task.id, idx)">保存</button>
                  <button class="btn btn-sm" style="font-size:11px;padding:2px 8px" @click="cancelEdit">取消</button>
                </template>
              </div>
            </div>
            <textarea
              v-if="editingKey === `${task.id}-${idx}`"
              v-model="editContent"
              class="form-textarea"
              rows="8"
              style="font-size:12px;font-family:monospace"
            />
            <pre v-else class="step-result-preview">{{ getStepResult(task, idx) }}</pre>
          </div>

          <!-- 运行中动画 -->
          <div v-if="idx === task.current_step && task.status === 'running'" class="step-running">
            <span class="pulse-dot"></span> 正在执行...
            <button class="btn btn-danger btn-sm" style="margin-left:8px" @click="cancelTask(task.id)">终止</button>
          </div>
        </div>
      </div>

      <!-- 展开详细消息 -->
      <details style="margin-top:12px">
        <summary style="cursor:pointer;color:var(--text-muted);font-size:13px">查看详细消息</summary>
        <div style="margin-top:8px">
          <MessageBubble
            v-for="msg in task.messages"
            :key="msg.id"
            :message="msg"
          />
        </div>
      </details>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '../api'
import MessageBubble from '../components/MessageBubble.vue'
import { useTaskPolling } from '../composables/useTaskPolling'
import { PIPELINE_STEPS } from '../constants/pipeline'
import type { Task, TokenSummary } from '../types'
import { agentLabel, formatTokenCount, getStepStatus, getStepStatusText, statusBadgeClass, statusLabel } from '../utils/taskDisplay'

const tasks = ref<Task[]>([])
const runningTasks = ref(new Set<string>())
const editingKey = ref<string | null>(null)
const editContent = ref('')
const tokenSummary = ref<TokenSummary | null>(null)
const { startMultiTaskPolling, stopAllMultiPolling } = useTaskPolling()

const pipelineSteps = PIPELINE_STEPS

const reversedTasks = computed(() => [...tasks.value].reverse())

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

function getStepResult(task: Task, idx: number): string {
  return task.step_results[String(idx)] || ''
}

function startEdit(taskId: string, idx: number, content: string) {
  editingKey.value = `${taskId}-${idx}`
  editContent.value = content
}

function cancelEdit() {
  editingKey.value = null
  editContent.value = ''
}

async function saveEdit(taskId: string, idx: number) {
  try {
    const updated = await api.updateStepResult(taskId, idx, editContent.value)
    const i = tasks.value.findIndex(t => t.id === taskId)
    if (i !== -1) tasks.value[i] = updated
    editingKey.value = null
    editContent.value = ''
  } catch (e) {
    alert('保存失败: ' + (e instanceof Error ? e.message : String(e)))
  }
}

async function loadTasks() {
  try {
    tasks.value = await api.getTasks()
  } catch (e) {
    console.error('Failed to load tasks:', e)
  }
}

async function loadTokenSummary() {
  try {
    tokenSummary.value = await api.getTokenSummary()
  } catch (e) {
    console.error('Failed to load token summary:', e)
  }
}

async function runStep(taskId: string) {
  runningTasks.value.add(taskId)
  try {
    const updated = await api.runStep(taskId)
    const i = tasks.value.findIndex(t => t.id === taskId)
    if (i !== -1) tasks.value[i] = updated
    if (updated.status === 'running') {
      startMultiTaskPolling(taskId, task => {
        const index = tasks.value.findIndex(t => t.id === task.id)
        if (index !== -1) tasks.value[index] = task
      })
    }
  } catch (e) {
    alert('执行步骤失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    runningTasks.value.delete(taskId)
  }
}

async function cancelTask(taskId: string) {
  try {
    const updated = await api.cancelTask(taskId)
    const i = tasks.value.findIndex(t => t.id === taskId)
    if (i !== -1) tasks.value[i] = updated
  } catch (e) {
    alert('终止任务失败: ' + (e instanceof Error ? e.message : String(e)))
  }
}

onMounted(async () => {
  await Promise.all([loadTasks(), loadTokenSummary()])
  for (const t of tasks.value) {
    if (t.status === 'running') {
      startMultiTaskPolling(t.id, task => {
        const index = tasks.value.findIndex(item => item.id === task.id)
        if (index !== -1) tasks.value[index] = task
      })
    }
  }
})

onUnmounted(() => {
  stopAllMultiPolling()
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
.token-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 8px;
}
.token-stat-item {
  text-align: center;
  padding: 8px;
  background: var(--bg-input);
  border-radius: var(--radius);
  border: 1px solid var(--border);
}
.token-stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
}
.token-stat-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}
.token-by-step {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.token-step-badge {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  background: rgba(245,158,11,0.08);
  color: #d97706;
  border: 1px solid rgba(245,158,11,0.2);
}
</style>
