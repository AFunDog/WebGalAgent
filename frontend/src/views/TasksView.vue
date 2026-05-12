<template>
  <div>
    <h2 class="page-title">任务历史</h2>

    <div v-if="tasks.length === 0" class="empty-state">
      <p>暂无任务，前往<router-link :to="{ name: 'pipeline' }">流水线</router-link>创建新任务</p>
    </div>

    <div v-for="task in reversedTasks" :key="task.id" class="card" style="margin-bottom:16px">
      <div class="card-header">
        <h3>{{ task.title || task.content.slice(0, 60) }}</h3>
        <div style="display:flex;gap:8px;align-items:center">
          <button
            v-if="task.status === 'running' || task.status === 'pending'"
            class="btn btn-danger btn-sm"
            :disabled="cancelling.has(task.id)"
            @click="cancelTask(task.id)"
          >
            {{ cancelling.has(task.id) ? '终止中...' : '终止' }}
          </button>
          <span class="badge" :class="statusBadgeClass(task.status)">{{ statusLabel(task.status) }}</span>
        </div>
      </div>
      <p style="color:var(--text-muted);font-size:12px">
        ID: {{ task.id }} · {{ formatTime(task.created_at) }}
      </p>
      <p
        v-if="task.errors.length"
        style="color:var(--danger);font-size:12px;margin-top:4px"
      >{{ task.errors.join('; ') }}</p>

      <!-- 节点图 -->
      <PipelineGraph
        :agents="agentDefs"
        :messages="task.messages"
        :active-agent="task.status === 'running' ? currentAgent(task) : ''"
        style="margin-top:16px"
      />

      <!-- 展开详情 -->
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
import PipelineGraph from '../components/PipelineGraph.vue'
import type { Task, AgentInfo } from '../types'

/** 固定 1 秒间隔的任务轮询 */
class TaskPoll {
  taskId: string
  timerId = 0
  attempts = 0
  onUpdate: ((task: Task) => void) | null = null
  onStop: (() => void) | null = null

  private static readonly INTERVAL = 1000

  constructor(taskId: string) {
    this.taskId = taskId
  }

  start(): void {
    this.scheduleNext()
  }

  stop(): void {
    if (this.timerId) {
      clearTimeout(this.timerId)
      this.timerId = 0
    }
    this.onStop?.()
  }

  private scheduleNext(): void {
    this.timerId = window.setTimeout(() => void this.tick(), TaskPoll.INTERVAL)
  }

  private async tick(): Promise<void> {
    this.attempts++
    try {
      const task = await api.getTask(this.taskId)
      this.onUpdate?.(task)
      if (task.status !== 'running' && task.status !== 'pending') {
        this.stop()
        return
      }
    } catch (e) {
      console.error('轮询任务状态失败:', e)
    }
    if (this.attempts >= 600) {
      this.stop()
      return
    }
    this.scheduleNext()
  }
}

const tasks = ref<Task[]>([])
const cancelling = ref(new Set<string>())
const agentDefs = ref<AgentInfo[]>([])

const activePolls = new Map<string, TaskPoll>()

const reversedTasks = computed(() => [...tasks.value].reverse())

const AGENT_ORDER = ['outline_writer', 'script_writer', 'script_converter']

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'completed': return 'badge-success'
    case 'running': return 'badge-warning'
    case 'failed': return 'badge-danger'
    case 'cancelled': return 'badge-danger'
    default: return 'badge-muted'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'completed': return '已完成'
    case 'running': return '运行中'
    case 'pending': return '等待中'
    case 'failed': return '失败'
    case 'cancelled': return '已取消'
    default: return status
  }
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

function currentAgent(task: Task): string {
  const resultMsgs = task.messages.filter(m => m.type === 'result')
  if (resultMsgs.length === 0) return 'outline_writer'
  const lastSender = resultMsgs[resultMsgs.length - 1]?.sender ?? ''
  const idx = AGENT_ORDER.indexOf(lastSender)
  if (idx >= 0 && idx < AGENT_ORDER.length - 1) return AGENT_ORDER[idx + 1]!
  return lastSender
}

function startPolling(taskId: string) {
  if (activePolls.has(taskId)) return
  const poll = new TaskPoll(taskId)
  poll.onUpdate = (task) => {
    const idx = tasks.value.findIndex(t => t.id === taskId)
    if (idx !== -1) {
      tasks.value[idx] = task
    }
  }
  poll.onStop = () => {
    activePolls.delete(taskId)
  }
  poll.start()
  activePolls.set(taskId, poll)
}

async function loadTasks() {
  try {
    tasks.value = await api.getTasks()
  } catch (e) {
    console.error('Failed to load tasks:', e)
  }
}

async function cancelTask(taskId: string) {
  cancelling.value.add(taskId)
  try {
    const updated = await api.cancelTask(taskId)
    const idx = tasks.value.findIndex(t => t.id === taskId)
    if (idx !== -1) {
      tasks.value[idx] = updated
    }
    const poll = activePolls.get(taskId)
    if (poll) {
      poll.stop()
      activePolls.delete(taskId)
    }
  } catch (e) {
    alert('终止任务失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    cancelling.value.delete(taskId)
  }
}

onMounted(async () => {
  await loadTasks()
  for (const t of tasks.value) {
    if (t.status === 'running' || t.status === 'pending') {
      startPolling(t.id)
    }
  }
  try {
    const info = await api.getPipeline()
    agentDefs.value = info.agents
  } catch (e) {
    console.error('Failed to load pipeline info:', e)
  }
})

onUnmounted(() => {
  activePolls.forEach(poll => poll.stop())
  activePolls.clear()
})
</script>
