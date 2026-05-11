<template>
  <div>
    <h2 class="page-title">任务执行</h2>

    <!-- 创建新任务 -->
    <div class="card" style="margin-bottom:24px">
      <div class="card-header"><h3>创建新任务</h3></div>
      <div class="form-group">
        <label>任务内容</label>
        <textarea
          v-model="newTaskContent"
          class="form-textarea"
          placeholder="请输入任务描述..."
          @keyup.ctrl.enter="createTask"
        />
      </div>
      <button class="btn btn-primary" :disabled="creating" @click="createTask">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px">
          <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
        执行任务
      </button>
    </div>

    <!-- 任务列表 -->
    <div v-if="tasks.length === 0" class="empty-state">
      <p>暂无任务，在上方创建新任务</p>
    </div>
    <div v-for="task in reversedTasks" :key="task.id" class="card">
      <div class="card-header">
        <h3>{{ task.content.slice(0, 80) }}</h3>
        <span class="badge" :class="statusBadgeClass(task.status)">{{ task.status }}</span>
      </div>
      <p style="color:var(--text-muted);font-size:12px">
        ID: {{ task.id }} · 创建时间: {{ formatTime(task.created_at) }}
      </p>
      <p
        v-if="task.errors.length"
        style="color:var(--danger);font-size:12px;margin-top:4px"
      >{{ task.errors.join('; ') }}</p>
      <div style="margin-top:12px">
        <MessageBubble
          v-for="msg in task.messages"
          :key="msg.id"
          :message="msg"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '../api'
import MessageBubble from '../components/MessageBubble.vue'
import type { Task } from '../types'

/** 带指数退避的任务轮询：2s → 3s → 5s → 8s（上限） */
class TaskPoll {
  taskId: string
  timerId = 0
  attempts = 0
  onUpdate: ((task: Task) => void) | null = null
  onStop: (() => void) | null = null

  private static readonly INTERVALS = [2000, 3000, 5000, 8000]

  constructor(taskId: string) {
    this.taskId = taskId
  }

  private get interval(): number {
    const idx = Math.min(this.attempts, TaskPoll.INTERVALS.length - 1)
    return TaskPoll.INTERVALS[idx]!
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
    this.timerId = window.setTimeout(() => void this.tick(), this.interval)
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
    // 超过 10 分钟停止
    if (this.attempts >= 100) {
      this.stop()
      return
    }
    this.scheduleNext()
  }
}

const tasks = ref<Task[]>([])
const newTaskContent = ref('')
const creating = ref(false)

// 轮询管理
const activePolls = new Map<string, TaskPoll>()

const reversedTasks = computed(() => [...tasks.value].reverse())

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'completed': return 'badge-success'
    case 'running': return 'badge-warning'
    case 'failed': return 'badge-danger'
    default: return 'badge-muted'
  }
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString()
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

async function createTask() {
  const content = newTaskContent.value.trim()
  if (!content) return
  creating.value = true
  try {
    const task = await api.createTask(content)
    newTaskContent.value = ''
    await loadTasks()
    startPolling(task.id)
  } catch (e) {
    alert('创建任务失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    creating.value = false
  }
}

async function loadTasks() {
  try {
    tasks.value = await api.getTasks()
  } catch (e) {
    console.error('Failed to load tasks:', e)
  }
}

onMounted(async () => {
  await loadTasks()
  // 对进行中的任务启动轮询
  for (const t of tasks.value) {
    if (t.status === 'running' || t.status === 'pending') {
      startPolling(t.id)
    }
  }
})

onUnmounted(() => {
  activePolls.forEach(poll => poll.stop())
  activePolls.clear()
})
</script>
