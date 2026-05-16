<template>
  <div>
    <h2 class="page-title">软链接管理</h2>

    <!-- 当前链接状态 -->
    <div class="card" style="margin-bottom:16px">
      <div class="card-header">
        <h3>链接状态</h3>
        <button class="btn btn-sm" @click="refreshStatus" :disabled="loading">
          {{ loading ? '刷新中...' : '刷新' }}
        </button>
      </div>
      <div v-if="linkStatus" class="link-status">
        <div class="status-row">
          <span class="status-label">链接路径:</span>
          <code>{{ linkStatus.path }}</code>
        </div>
        <div class="status-row">
          <span class="status-label">存在:</span>
          <span :class="linkStatus.exists ? 'text-success' : 'text-muted'">
            {{ linkStatus.exists ? '是' : '否' }}
          </span>
        </div>
        <div class="status-row">
          <span class="status-label">类型:</span>
          <span>{{ linkStatus.is_symlink ? '符号链接' : (linkStatus.exists ? '普通目录' : '-') }}</span>
        </div>
        <div v-if="linkStatus.target" class="status-row">
          <span class="status-label">指向:</span>
          <code>{{ linkStatus.target }}</code>
        </div>
        <div class="status-row">
          <span class="status-label">有效:</span>
          <span :class="linkStatus.valid ? 'text-success' : 'text-danger'">
            {{ linkStatus.valid ? '是' : '否' }}
          </span>
        </div>
      </div>
      <div v-else class="empty-state">
        <p>加载中...</p>
      </div>
    </div>

    <!-- 创建软链接 -->
    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><h3>创建软链接</h3></div>
      <div class="form-group">
        <label>选择任务</label>
        <select v-model="selectedTaskId" class="form-select">
          <option value="">-- 请选择任务 --</option>
          <option v-for="taskId in taskList" :key="taskId" :value="taskId">
            {{ taskId }}
          </option>
        </select>
      </div>
      <div class="form-group">
        <label>链接路径（可选）</label>
        <input
          v-model="customLinkPath"
          type="text"
          class="form-input"
          placeholder="留空使用默认: D:\Data\WebGal\scene"
        />
      </div>
      <div class="form-group">
        <label>
          <input v-model="forceOverwrite" type="checkbox" />
          强制覆盖已存在的链接
        </label>
      </div>
      <button
        class="btn btn-primary"
        @click="createLink"
        :disabled="!selectedTaskId || creating"
      >
        {{ creating ? '创建中...' : '创建软链接' }}
      </button>
      <p v-if="resultMessage" :class="resultSuccess ? 'text-success' : 'text-danger'" style="margin-top:8px">
        {{ resultMessage }}
      </p>
    </div>

    <!-- 快速操作 -->
    <div class="card">
      <div class="card-header"><h3>快速操作</h3></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn" @click="removeLink" :disabled="!linkStatus?.exists || removing">
          {{ removing ? '删除中...' : '删除软链接' }}
        </button>
        <button class="btn" @click="openInExplorer" :disabled="!linkStatus?.exists">
          在资源管理器中打开
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api'
import type { LinkStatus } from '../types'

const loading = ref(false)
const creating = ref(false)
const removing = ref(false)
const taskList = ref<string[]>([])
const selectedTaskId = ref('')
const customLinkPath = ref('')
const forceOverwrite = ref(false)
const linkStatus = ref<LinkStatus | null>(null)
const resultMessage = ref('')
const resultSuccess = ref(false)

async function refreshStatus() {
  loading.value = true
  try {
    linkStatus.value = await api.getLinkStatus()
  } catch (e) {
    console.error('Failed to load link status:', e)
  } finally {
    loading.value = false
  }
}

async function loadTasks() {
  try {
    taskList.value = await api.listTasks()
  } catch (e) {
    console.error('Failed to load tasks:', e)
  }
}

async function createLink() {
  if (!selectedTaskId.value) return
  creating.value = true
  resultMessage.value = ''
  try {
    const res = await api.createLink(
      selectedTaskId.value,
      customLinkPath.value || undefined,
      forceOverwrite.value
    )
    resultMessage.value = res.message
    resultSuccess.value = res.success
    if (res.success) {
      await refreshStatus()
    }
  } catch (e) {
    resultMessage.value = '创建失败: ' + (e instanceof Error ? e.message : String(e))
    resultSuccess.value = false
  } finally {
    creating.value = false
  }
}

async function removeLink() {
  if (!linkStatus.value?.exists) return
  if (!confirm('确定要删除软链接吗？')) return
  removing.value = true
  resultMessage.value = ''
  try {
    const res = await api.removeLink()
    resultMessage.value = res.message
    resultSuccess.value = res.success
    if (res.success) {
      await refreshStatus()
    }
  } catch (e) {
    resultMessage.value = '删除失败: ' + (e instanceof Error ? e.message : String(e))
    resultSuccess.value = false
  } finally {
    removing.value = false
  }
}

function openInExplorer() {
  if (linkStatus.value?.target) {
    window.open('file:///' + linkStatus.value.target.replace(/\\/g, '/'))
  }
}

onMounted(async () => {
  await Promise.all([refreshStatus(), loadTasks()])
})
</script>

<style scoped>
.link-status {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.status-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.status-label {
  min-width: 80px;
  color: var(--text-muted);
  font-size: 13px;
}
code {
  background: var(--bg-input);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
}
.text-success {
  color: var(--success);
}
.text-danger {
  color: var(--danger);
}
.text-muted {
  color: var(--text-muted);
}
</style>
