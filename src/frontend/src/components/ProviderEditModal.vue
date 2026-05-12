<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="emit('cancel')">
      <div class="modal">
        <h2>编辑 — {{ agentLabel }}</h2>

        <div class="form-group">
          <label>快捷预设</label>
          <div style="display:flex;gap:8px">
            <select v-model="selectedPreset" class="form-select" style="flex:1">
              <option value="">选择预设...</option>
              <option v-for="(_, name) in presets" :key="name" :value="name">
                {{ name }}
              </option>
            </select>
            <button class="btn btn-ghost btn-sm" @click="applyPreset">应用</button>
          </div>
        </div>

        <div class="grid-2">
          <div class="form-group">
            <label>提供商 (Provider)</label>
            <input v-model="form.provider" class="form-input" />
          </div>
          <div class="form-group">
            <label>模型 (Model)</label>
            <input v-model="form.model" class="form-input" />
          </div>
        </div>

        <div class="form-group">
          <label>Base URL</label>
          <input v-model="form.base_url" class="form-input" />
        </div>

        <div class="form-group">
          <label>API Key</label>
          <input
            v-model="form.api_key"
            class="form-input"
            type="password"
            placeholder="sk-..."
          />
        </div>

        <div class="grid-2">
          <div class="form-group">
            <label>Temperature</label>
            <input
              v-model.number="form.temperature"
              class="form-input"
              type="number"
              step="0.1"
              min="0"
              max="2"
            />
          </div>
          <div class="form-group">
            <label>Max Tokens</label>
            <input
              v-model.number="form.max_tokens"
              class="form-input"
              type="number"
              min="1"
            />
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-ghost" @click="emit('cancel')">取消</button>
          <button class="btn btn-primary" @click="emit('save', { ...form })">保存</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import type { ProviderConfig, ProviderPresets } from '../types'

const AGENT_LABELS: Record<string, string> = {
  __defaults__: '默认配置',
  outline_writer: 'A: 剧本大纲编写',
  script_writer: 'B: 章节剧本生成',
  script_converter: 'C: WebGal 脚本转换',
}

const props = defineProps<{
  agentName: string
  config: ProviderConfig
  presets: ProviderPresets
}>()

const emit = defineEmits<{
  cancel: []
  save: [config: ProviderConfig]
}>()

const agentLabel = AGENT_LABELS[props.agentName] ?? props.agentName

const form = reactive<ProviderConfig>({ ...props.config })
const selectedPreset = ref('')

function applyPreset() {
  if (!selectedPreset.value) return
  const preset = props.presets[selectedPreset.value]
  if (!preset) return
  form.provider = preset.provider ?? selectedPreset.value
  form.base_url = preset.base_url ?? ''
}
</script>
