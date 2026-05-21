<template>
  <div>
    <h2 class="page-title">提供商配置</h2>
    <p class="section-intro">
      配置每个智能体使用的 LLM 提供商、模型和参数。未单独配置的智能体将使用默认配置。
    </p>

    <!-- 默认配置 -->
    <div v-if="defaults" class="card">
      <div class="card-header">
        <h3>默认配置</h3>
        <button class="btn btn-ghost btn-sm" @click="openEdit('__defaults__')">编辑</button>
      </div>
      <div class="compact-meta" style="margin-bottom:8px">{{ defaults.provider }} / {{ defaults.model }}</div>
      <details class="details-panel">
        <summary>
          <span>查看默认配置明细</span>
          <span class="summary-chevron">▶</span>
        </summary>
        <div class="details-panel__body">
          <ProviderFields :config="defaults" />
        </div>
      </details>
    </div>

    <!-- 智能体配置 -->
    <h3 style="margin:18px 0 10px;font-size:14px">智能体配置</h3>
    <div v-for="(cfg, name) in agents" :key="name" class="card">
      <div class="card-header">
        <h3>{{ AGENT_LABELS[name] ?? name }}</h3>
        <div style="display:flex;gap:6px;align-items:center">
          <span class="tag">{{ cfg.provider }}/{{ cfg.model }}</span>
          <button class="btn btn-ghost btn-sm" @click="openEdit(name)">编辑</button>
        </div>
      </div>
      <details class="details-panel">
        <summary>
          <span>查看该智能体配置明细</span>
          <span class="summary-chevron">▶</span>
        </summary>
        <div class="details-panel__body">
          <ProviderFields :config="cfg" />
        </div>
      </details>
    </div>

    <!-- 编辑模态框 -->
    <ProviderEditModal
      v-if="editingAgent !== null"
      :agent-name="editingAgent"
      :config="editingConfig"
      :presets="presets"
      @cancel="editingAgent = null"
      @save="saveProvider"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import ProviderFields from '../components/ProviderFields.vue'
import ProviderEditModal from '../components/ProviderEditModal.vue'
import type { ProviderConfig, ProviderData, ProviderPresets } from '../types'

const AGENT_LABELS: Record<string, string> = {
  outline_writer: 'A: 剧本大纲编写',
  script_writer: 'B: 章节剧本生成',
  script_converter: 'C: WebGal 脚本转换',
}

const providerData = ref<ProviderData | null>(null)
const presets = ref<ProviderPresets>({})
const editingAgent = ref<string | null>(null)

const defaults = computed(() => providerData.value?.defaults ?? null)
const agents = computed(() => providerData.value?.agents ?? {})

const editingConfig = computed<ProviderConfig>(() => {
  if (!editingAgent.value || !providerData.value) {
    return { provider: '', model: '', base_url: '', api_key: '', temperature: 0.7, max_tokens: 4096 }
  }
  if (editingAgent.value === '__defaults__') {
    return providerData.value.defaults
  }
  return providerData.value.agents[editingAgent.value] ?? providerData.value.defaults
})

function openEdit(agentName: string) {
  editingAgent.value = agentName
}

async function saveProvider(config: ProviderConfig) {
  if (!editingAgent.value) return
  try {
    if (editingAgent.value === '__defaults__') {
      await api.saveDefaultProvider(config)
    } else {
      await api.saveAgentProvider(editingAgent.value, config)
    }
    editingAgent.value = null
    await loadProviders()
  } catch (e) {
    alert('保存失败: ' + (e instanceof Error ? e.message : String(e)))
  }
}

async function loadProviders() {
  try {
    const [data, pres] = await Promise.all([
      api.getProviders(),
      api.getPresets(),
    ])
    providerData.value = data
    presets.value = pres
  } catch (e) {
    console.error('Failed to load providers:', e)
  }
}

onMounted(loadProviders)
</script>
