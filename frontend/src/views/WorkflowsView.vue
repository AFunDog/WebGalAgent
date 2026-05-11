<template>
  <div>
    <h2 class="page-title">工作流</h2>

    <!-- 流程描述 -->
    <div class="card" style="margin-bottom:20px">
      <p style="color:var(--text-muted);font-size:14px">{{ workflowInfo?.description ?? '' }}</p>
    </div>

    <!-- 流程步骤 -->
    <template v-if="workflowInfo">
      <template v-for="(agent, i) in workflowInfo.agents" :key="agent.name">
        <div class="card">
          <div class="card-header">
            <h3>{{ stepLabels[i] ?? agent.name }}</h3>
            <div>
              <span class="badge badge-muted">{{ agent.name }}</span>
              <span class="tag" style="margin-left:4px">{{ agent.provider }}/{{ agent.model }}</span>
            </div>
          </div>
          <p style="color:var(--text-muted);font-size:13px">{{ agent.description }}</p>
        </div>
        <div
          v-if="i < workflowInfo.agents.length - 1"
          :key="'arrow-' + i"
          style="text-align:center;color:var(--text-muted);font-size:24px;padding:4px 0"
        >↓</div>
      </template>
    </template>
    <div v-else class="empty-state"><p>加载中...</p></div>

    <!-- 智能体状态 -->
    <div class="card" style="margin-top:20px">
      <div class="card-header"><h3>智能体状态</h3></div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>名称</th><th>描述</th><th>提供商</th><th>模型</th><th>状态</th></tr>
          </thead>
          <tbody>
            <tr v-if="agentStatus.length === 0">
              <td colspan="5" style="color:var(--text-muted)">加载中...</td>
            </tr>
            <tr v-for="a in agentStatus" :key="a.name">
              <td><strong>{{ a.name }}</strong></td>
              <td style="color:var(--text-muted)">{{ a.description }}</td>
              <td><span class="tag">{{ a.provider || '-' }}</span></td>
              <td>{{ a.model || '-' }}</td>
              <td>
                <span class="badge" :class="a.state === 'idle' ? 'badge-muted' : 'badge-success'">
                  {{ a.state }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api'
import type { WorkflowInfo, AgentInfo } from '../types'

const stepLabels = ['A: 编写剧本大纲', 'B: 生成章节剧本', 'C: 转换为 WebGal 脚本']

const workflowInfo = ref<WorkflowInfo | null>(null)
const agentStatus = ref<AgentInfo[]>([])

onMounted(async () => {
  try {
    workflowInfo.value = await api.getPipeline()
  } catch (e) {
    console.error('Failed to load workflow:', e)
  }
  try {
    agentStatus.value = await api.getAgentStatus()
  } catch (e) {
    console.error('Failed to load agent status:', e)
  }
})
</script>
