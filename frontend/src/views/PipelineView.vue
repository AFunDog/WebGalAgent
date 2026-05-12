<template>
  <div>
    <h2 class="page-title">流水线</h2>

    <!-- 流水线节点图 -->
    <PipelineGraph
      :agents="agentDefs"
      :messages="[]"
      active-agent=""
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
      <button class="btn btn-primary" :disabled="creating" @click="createTask">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px">
          <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
        执行任务
      </button>
      <p v-if="latestTask" style="margin-top:12px;font-size:13px">
        <router-link :to="{ name: 'tasks' }">查看任务历史</router-link>
        <span v-if="latestTask.status === 'running' || latestTask.status === 'pending'" style="color:var(--text-muted)">
           · 最新任务运行中...
        </span>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api'
import PipelineGraph from '../components/PipelineGraph.vue'
import type { AgentInfo, Task } from '../types'

const agentDefs = ref<AgentInfo[]>([])
const newTaskContent = ref('')
const creating = ref(false)
const latestTask = ref<Task | null>(null)

async function createTask() {
  const content = newTaskContent.value.trim()
  if (!content) return
  creating.value = true
  try {
    const task = await api.createTask(content)
    newTaskContent.value = ''
    latestTask.value = task
  } catch (e) {
    alert('创建任务失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  try {
    const info = await api.getPipeline()
    agentDefs.value = info.agents
  } catch (e) {
    console.error('Failed to load pipeline info:', e)
  }
})
</script>
