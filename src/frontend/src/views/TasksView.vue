<template>
  <div>
    <h2 class="page-title">任务历史</h2>

    <!-- 顶部汇总：跨任务统计整体 token 消耗 -->
    <details v-if="tokenSummary && tokenSummary.total_tokens > 0" class="details-panel" style="margin-bottom:12px">
      <summary>
        <span>Token 消耗统计</span>
        <span class="summary-chevron">▶</span>
      </summary>
      <div class="details-panel__body">
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
    </details>

    <!-- 空状态：当前还没有任何落盘任务 -->
    <div v-if="tasks.length === 0" class="empty-state">
      <p>暂无任务，前往<router-link :to="{ name: 'pipeline' }">流水线</router-link>创建新任务</p>
    </div>

    <!-- 任务列表：按时间倒序展示，默认折叠，仅在展开时显示完整步骤与消息 -->
    <details v-for="task in reversedTasks" :key="task.id" class="task-card card">
      <summary class="task-card__summary">
        <div class="task-card__summary-main">
          <div class="task-card__title-row">
            <h3 class="task-card__title">{{ task.title || task.content.slice(0, 60) }}</h3>
            <span class="badge" :class="statusBadgeClass(task.status)">{{ statusLabel(task.status) }}</span>
          </div>
          <div class="task-card__meta">
            <span>任务 {{ task.id }}</span>
            <span>{{ formatTime(task.created_at) }}</span>
            <span>步骤 {{ task.current_step }}/{{ pipelineSteps.length }}</span>
            <span v-if="task.total_tokens > 0">{{ formatTokenCount(task.total_tokens) }} tokens</span>
            <span v-if="task.errors.length" class="task-card__error-count">{{ task.errors.length }} 个错误</span>
          </div>
          <div class="task-card__preview">
            {{ getTaskPreview(task) }}
          </div>
        </div>
        <span class="summary-chevron task-card__chevron">▶</span>
      </summary>

      <div class="task-card__body">
        <p
          v-if="task.errors.length"
          style="color:var(--danger);font-size:12px;margin-bottom:8px"
        >{{ task.errors.join('; ') }}</p>

        <!-- 步骤列表：与流水线页保持一致的视觉结构，但支持多任务并发观察 -->
        <div class="step-list">
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

            <!-- 当前步骤操作区 -->
            <button
              v-if="idx === task.current_step && task.status !== 'running' && task.status !== 'completed'"
              class="btn btn-primary btn-sm"
              :disabled="runningTasks.has(task.id)"
              @click="runStep(task.id)"
              style="margin-top:8px"
            >
              {{ runningTasks.has(task.id) ? '执行中...' : '执行此步骤' }}
            </button>

            <!-- 历史结果查看与修订区 -->
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
              <div class="step-revise-box">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                  <span style="font-size:12px;color:var(--text-muted)">额外修订要求</span>
                  <button
                    class="btn btn-primary btn-sm"
                    style="font-size:11px;padding:2px 8px"
                    :disabled="runningTasks.has(task.id) || !getRevisionInstruction(task.id, idx).trim()"
                    @click="reviseStep(task.id, idx)"
                  >按反馈重生成</button>
                </div>
                <textarea
                  :value="getRevisionInstruction(task.id, idx)"
                  class="form-textarea"
                  rows="3"
                  placeholder="例如：保留结构，但对白更自然，减少解释性旁白。"
                  style="font-size:12px"
                  @input="setRevisionInstruction(task.id, idx, ($event.target as HTMLTextAreaElement).value)"
                />
              </div>
            </div>

            <!-- 运行中反馈区 -->
            <div v-if="idx === task.current_step && task.status === 'running'" class="step-running">
              <span class="pulse-dot"></span> 正在执行...
              <button class="btn btn-danger btn-sm" style="margin-left:8px" @click="cancelTask(task.id)">终止</button>
            </div>
          </div>
        </div>

        <!-- 明细消息区：保留完整消息链，便于排查 agent 输出 -->
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
    </details>
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
const revisionInstructions = ref<Record<string, string>>({})
const tokenSummary = ref<TokenSummary | null>(null)
const { startMultiTaskPolling, stopAllMultiPolling } = useTaskPolling()

// 这个页面维护的是“任务集合”而不是单任务详情，因此所有写回都按 taskId 定位。

// 任务历史页与流水线页共享同一套步骤定义，避免展示层自己维护流程顺序。
const pipelineSteps = PIPELINE_STEPS

const reversedTasks = computed(() => [...tasks.value].reverse())

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

function getTaskPreview(task: Task): string {
  const contentPreview = task.title || task.content.slice(0, 80)
  const cleaned = contentPreview.replace(/\s+/g, ' ').trim()
  if (cleaned.length <= 80) return cleaned || '无标题任务'
  return cleaned.slice(0, 80) + '…'
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

function getRevisionInstruction(taskId: string, idx: number): string {
  return revisionInstructions.value[`${taskId}-${idx}`] || ''
}

function setRevisionInstruction(taskId: string, idx: number, value: string) {
  revisionInstructions.value[`${taskId}-${idx}`] = value
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

async function reviseStep(taskId: string, idx: number) {
  const instruction = getRevisionInstruction(taskId, idx).trim()
  if (!instruction) {
    alert('请先填写额外修订要求')
    return
  }
  runningTasks.value.add(taskId)
  try {
    const updated = await api.reviseStep(taskId, idx, instruction)
    const i = tasks.value.findIndex(t => t.id === taskId)
    if (i !== -1) tasks.value[i] = updated
    if (updated.status === 'running') {
      startMultiTaskPolling(taskId, task => {
        const index = tasks.value.findIndex(t => t.id === task.id)
        if (index !== -1) tasks.value[index] = task
      })
    }
  } catch (e) {
    alert('重生成失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    runningTasks.value.delete(taskId)
  }
}

// 初始化拆成“任务快照”和“统计快照”两类请求，避免页面层拼接接口返回结构。
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

// 历史页允许并发观察多个运行中的任务，因此使用 multi-task polling 管理器。
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
  // 初次进入时先拉快照，再只为真正 running 的任务挂轮询。
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
  // 离开页面时统一停掉所有轮询，避免旧页面继续写回响应式状态。
  stopAllMultiPolling()
})
</script>

<style scoped>
.step-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-card {
  margin-bottom: 16px;
  overflow: hidden;
}

.task-card__summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  padding: 14px 16px;
}

.task-card__summary::-webkit-details-marker {
  display: none;
}

.task-card__summary-main {
  min-width: 0;
  flex: 1;
}

.task-card__title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.task-card__title {
  min-width: 0;
  font-size: 15px;
  font-weight: 800;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-muted);
}

.task-card__meta span {
  position: relative;
}

.task-card__meta span:not(:last-child)::after {
  content: '·';
  margin-left: 10px;
  color: var(--text-muted);
}

.task-card__preview {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-soft);
  line-height: 1.5;
  max-width: 920px;
}

.task-card__error-count {
  color: var(--danger);
}

.task-card__chevron {
  margin-top: 2px;
  transition: transform 0.18s ease;
}

.task-card[open] .task-card__chevron {
  transform: rotate(90deg);
}

.task-card__body {
  padding: 0 16px 16px;
}

.task-card > summary {
  border-bottom: 1px solid var(--border);
}

.task-card[open] > summary {
  border-bottom-color: rgba(255, 255, 255, 0.06);
}

.task-card:hover > summary {
  background: rgba(255, 255, 255, 0.02);
}
.step-item {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 12px;
  transition: border-color 0.2s;
}
.step-item.step-active {
  border-color: var(--primary-hover);
  background: rgba(247, 99, 12, 0.05);
}
.step-item.step-done {
  border-color: var(--success);
  background: rgba(93, 211, 158, 0.04);
}
.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.step-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: var(--border);
}
.step-active .step-index { background: var(--primary-hover); }
.step-done .step-index { background: var(--success); }
.step-name {
  font-weight: 600;
  font-size: 13px;
}
.step-status {
  margin-left: auto;
  font-size: 11px;
  font-weight: 500;
}
.step-status-done { color: var(--success); }
.step-status-running { color: var(--primary-hover); }
.step-status-ready { color: var(--warning); }
.step-status-pending { color: var(--text-muted); }
.step-result {
  margin-top: 8px;
}
.step-revise-box {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--border);
}
.step-result-preview {
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px;
  font-size: 11px;
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
  font-size: 12px;
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
  font-size: 10px;
  font-weight: 500;
  background: rgba(245,158,11,0.12);
  color: #d97706;
}
.token-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-top: 6px;
}
.token-stat-item {
  text-align: center;
  padding: 8px 6px;
  background: var(--bg-input);
  border-radius: var(--radius);
  border: 1px solid var(--border);
}
.token-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}
.token-stat-label {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 2px;
}
.token-by-step {
  display: flex;
  gap: 8px;
  margin-top: 6px;
  flex-wrap: wrap;
}
.token-step-badge {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  background: rgba(245,158,11,0.08);
  color: #d97706;
  border: 1px solid rgba(245,158,11,0.2);
}
</style>
