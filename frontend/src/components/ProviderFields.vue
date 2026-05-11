<template>
  <div class="provider-info">
    <div class="provider-field">
      <span class="provider-label">提供商</span>
      <span>{{ config.provider }}</span>
    </div>
    <div class="provider-field">
      <span class="provider-label">模型</span>
      <span>{{ config.model }}</span>
    </div>
    <div class="provider-field">
      <span class="provider-label">Base URL</span>
      <span class="provider-url">{{ config.base_url }}</span>
    </div>
    <div class="provider-field">
      <span class="provider-label">API Key</span>
      <span>{{ config.api_key ? '••••••••' : '未设置' }}</span>
    </div>
    <div class="provider-field">
      <span class="provider-label">Temperature</span>
      <span>{{ config.temperature }}</span>
    </div>
    <div class="provider-field">
      <span class="provider-label">Max Tokens</span>
      <span>{{ config.max_tokens }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ProviderConfig } from '../types'

defineProps<{
  config: ProviderConfig
}>()
</script>
