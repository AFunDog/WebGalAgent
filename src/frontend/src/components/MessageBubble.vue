<template>
  <div class="msg-bubble" :class="message.type">
    <div>
      <strong>{{ message.sender }}</strong> → <strong>{{ message.receiver }}</strong>
    </div>
    <div style="white-space:pre-wrap;margin-top:4px">{{ message.content }}</div>

    <div v-if="toolCalls.length > 0" class="tool-calls">
      <div style="color:var(--text-muted);margin-bottom:4px">
        🔧 工具调用 ({{ toolCalls.length }})
      </div>
      <div
        v-for="(tc, i) in toolCalls"
        :key="i"
        class="tool-call-item"
        :class="{ failed: !tc.success }"
      >
        <strong>{{ tc.tool }}</strong>(
        {{ formatArgs(tc.args) }}
        )
        <span v-if="!tc.success" style="color:var(--danger)"> ✗</span>
        <details style="margin-top:2px">
          <summary style="cursor:pointer;color:var(--text-muted)">结果</summary>
          <pre class="tool-call-result">{{ formatResult(tc.result) }}</pre>
        </details>
      </div>
    </div>

    <div class="msg-meta">
      {{ message.type }} · {{ formatTime(message.created_at) }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TaskMessage, ToolCallRecord } from '../types'

const props = defineProps<{
  message: TaskMessage
}>()

const toolCalls = computed<ToolCallRecord[]>(() => {
  const tc = props.message.metadata?.tool_calls
  return Array.isArray(tc) ? tc : []
})

function formatArgs(args: Record<string, unknown>): string {
  return Object.entries(args)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(', ')
}

function formatResult(result: unknown): string {
  if (typeof result === 'string') return result
  return JSON.stringify(result, null, 2)
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString()
}
</script>
