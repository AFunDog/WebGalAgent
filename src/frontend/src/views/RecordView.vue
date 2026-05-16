<template>
  <div>
    <h2 class="page-title">浏览器录制</h2>

    <!-- 录制配置 -->
    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><h3>录制配置</h3></div>

      <div class="form-group">
        <label>目标 URL</label>
        <input
          v-model="config.url"
          type="text"
          class="form-input"
          placeholder="https://example.com"
        />
      </div>

      <div class="form-group">
        <label>录制目标选择器</label>
        <input
          v-model="config.canvas_selector"
          type="text"
          class="form-input"
          placeholder="div._MainStage_main_9enex_1"
        />
        <small style="color:var(--text-muted);font-size:11px">
          CSS 选择器，用于指定要录制的页面元素
        </small>
      </div>

      <div class="form-row">
        <div class="form-group" style="flex:1">
          <label>录制时长（秒）</label>
          <input
            v-model.number="config.duration"
            type="number"
            class="form-input"
            min="1"
            max="300"
            step="0.5"
          />
        </div>
        <div class="form-group" style="flex:1">
          <label>帧率 (FPS)</label>
          <input
            v-model.number="config.fps"
            type="number"
            class="form-input"
            min="1"
            max="60"
          />
        </div>
      </div>

      <div class="form-group">
        <label>浏览器类型</label>
        <select v-model="config.browser_type" class="form-select">
          <option value="chromium">Chromium</option>
          <option value="firefox">Firefox</option>
          <option value="webkit">WebKit</option>
        </select>
      </div>

      <div class="form-group">
        <label>
          <input v-model="config.headless" type="checkbox" />
          无头模式（不显示浏览器窗口）
        </label>
      </div>

      <div class="form-group">
        <label>浏览器可执行文件路径（可选）</label>
        <input
          v-model="config.executable_path"
          type="text"
          class="form-input"
          placeholder="留空使用默认浏览器"
        />
        <small style="color:var(--text-muted);font-size:11px">
          如使用 chrome-headless-shell 可获得更好的录制效果
        </small>
      </div>

      <div class="form-group">
        <label>输出路径（可选）</label>
        <input
          v-model="config.output_path"
          type="text"
          class="form-input"
          placeholder="留空使用默认路径: data/temp/record_xxx.mp4"
        />
      </div>

      <div style="display:flex;gap:8px">
        <button
          class="btn btn-primary"
          @click="startRecord"
          :disabled="recording || !config.url"
        >
          <svg v-if="!recording" viewBox="0 0 24 24" fill="currentColor" style="width:16px;height:16px">
            <circle cx="12" cy="12" r="8"/>
          </svg>
          {{ recording ? '录制中...' : '开始录制' }}
        </button>
        <button
          v-if="recording"
          class="btn btn-danger"
          @click="stopRecord"
        >
          停止
        </button>
      </div>
    </div>

    <!-- 录制结果 -->
    <div v-if="result" class="card">
      <div class="card-header">
        <h3>录制结果</h3>
        <span :class="result.success ? 'badge badge-success' : 'badge badge-danger'">
          {{ result.success ? '成功' : '失败' }}
        </span>
      </div>
      <div class="result-info">
        <div class="result-row">
          <span class="result-label">消息:</span>
          <span>{{ result.message }}</span>
        </div>
        <div v-if="result.output_path" class="result-row">
          <span class="result-label">输出路径:</span>
          <code>{{ result.output_path }}</code>
        </div>
        <div v-if="result.total_frames" class="result-row">
          <span class="result-label">总帧数:</span>
          <span>{{ result.total_frames }}</span>
        </div>
        <div v-if="result.duration" class="result-row">
          <span class="result-label">时长:</span>
          <span>{{ result.duration.toFixed(2) }} 秒</span>
        </div>
        <div v-if="result.file_size_mb" class="result-row">
          <span class="result-label">文件大小:</span>
          <span>{{ result.file_size_mb.toFixed(2) }} MB</span>
        </div>
      </div>
      <button v-if="result.success && result.output_path" class="btn" @click="openFile(result.output_path)">
        在资源管理器中打开
      </button>
    </div>

    <!-- 录制状态 -->
    <div v-if="recording" class="card">
      <div class="card-header"><h3>录制进度</h3></div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progress + '%' }"></div>
      </div>
      <p style="text-align:center;margin-top:8px">{{ progress.toFixed(0) }}%</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { api } from '../api'
import type { RecordConfig, RecordResult } from '../types'

const recording = ref(false)
const progress = ref(0)
const result = ref<RecordResult | null>(null)

const config = reactive<{
  url: string
  output_path: string
  duration: number
  fps: number
  canvas_selector: string
  browser_type: string
  headless: boolean
  executable_path: string
}>({
  url: '',
  output_path: '',
  duration: 5.0,
  fps: 30,
  canvas_selector: 'div._MainStage_main_9enex_1',
  browser_type: 'chromium',
  headless: false,
  executable_path: '',
})

async function startRecord() {
  if (!config.url) return
  recording.value = true
  progress.value = 0
  result.value = null

  // 模拟进度
  const progressTimer = setInterval(() => {
    if (progress.value < 90) {
      progress.value += Math.random() * 10
    }
  }, 500)

  try {
    const recordConfig: RecordConfig = {
      url: config.url,
      output_path: config.output_path || '',
      duration: config.duration,
      fps: config.fps,
      canvas_selector: config.canvas_selector,
    }
    result.value = await api.startRecord(recordConfig)
  } catch (e) {
    result.value = {
      success: false,
      message: '录制失败: ' + (e instanceof Error ? e.message : String(e)),
      output_path: null,
      total_frames: 0,
      duration: 0,
      file_size_mb: 0,
    }
  } finally {
    clearInterval(progressTimer)
    progress.value = 100
    recording.value = false
  }
}

async function stopRecord() {
  try {
    await api.stopRecord()
    recording.value = false
  } catch (e) {
    console.error('Stop record failed:', e)
  }
}

function openFile(path: string) {
  window.open('file:///' + path.replace(/\\/g, '/'))
}
</script>

<style scoped>
.form-row {
  display: flex;
  gap: 16px;
}
.result-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}
.result-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.result-label {
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
.progress-bar {
  height: 8px;
  background: var(--bg-input);
  border-radius: 4px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--primary-hover);
  transition: width 0.3s;
}
</style>
