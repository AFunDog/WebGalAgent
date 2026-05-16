<template>
  <div>
    <h2 class="page-title">浏览器录制</h2>

    <!-- 配置加载状态 -->
    <div v-if="configError" class="card" style="margin-bottom:16px; background: #3a1f1f;">
      <div style="padding:12px; color: #ff6b6b;">
        ⚠️ 配置加载失败: {{ configError }}
      </div>
    </div>

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
        <label>场景路径 (changeScene)</label>
        <input
          v-model="config.scene_path"
          type="text"
          class="form-input"
          placeholder="index.txt"
        />
        <small style="color:var(--text-muted);font-size:11px">
          调用 window.changeScene(path, 1) 时传入的场景文件路径
        </small>
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

      <div class="form-row">
        <div class="form-group" style="flex:1">
          <label>截图格式</label>
          <select v-model="config.format" class="form-select">
            <option value="jpeg">JPEG（有损，小文件）</option>
            <option value="png">PNG（无损，画质最好）</option>
          </select>
        </div>
        <div class="form-group" style="flex:1">
          <label>截图质量</label>
          <input
            v-model.number="config.quality"
            type="number"
            class="form-input"
            min="1"
            max="100"
          />
          <small style="color:var(--text-muted);font-size:11px">
            1-100，仅 JPEG 格式有效
          </small>
        </div>
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
        <div v-if="result.source_fps" class="result-row">
          <span class="result-label">源帧率:</span>
          <span>{{ result.source_fps.toFixed(2) }} FPS</span>
        </div>
        <div v-if="result.output_fps" class="result-row">
          <span class="result-label">输出帧率:</span>
          <span>{{ result.output_fps.toFixed(2) }} FPS</span>
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
      <!-- 实时日志 -->
      <div v-if="logs.length" class="record-log">
        <div v-for="(line, i) in logs" :key="i" class="log-line">{{ line }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { api } from '../api'
import type { RecordConfig, RecordResult } from '../types'

const recording = ref(false)
const progress = ref(0)
const result = ref<RecordResult | null>(null)
const logs = ref<string[]>([])
const configLoaded = ref(false)
const configError = ref('')

const config = reactive<{
  url: string
  output_path: string
  duration: number
  fps: number
  canvas_selector: string
  scene_path: string
  browser_type: string
  headless: boolean
  executable_path: string
  format: 'jpeg' | 'png'
  quality: number
}>({
  url: '',
  output_path: '',
  duration: 5.0,
  fps: 30,
  canvas_selector: 'div._MainStage_main_9enex_1',
  scene_path: 'index.txt',
  browser_type: 'chromium',
  headless: false,
  executable_path: '',
  format: 'jpeg',
  quality: 90,
})

// 页面加载时从后端获取配置默认值
onMounted(async () => {
  try {
    const serverConfig = await api.getRecordConfig()
    configLoaded.value = true
    if (serverConfig.url) config.url = serverConfig.url
    if (serverConfig.format) config.format = serverConfig.format
    if (serverConfig.quality) config.quality = serverConfig.quality
    if (serverConfig.fps) config.fps = serverConfig.fps
    if (serverConfig.duration) config.duration = serverConfig.duration
    if (serverConfig.canvas_selector) config.canvas_selector = serverConfig.canvas_selector
    if (serverConfig.scene_path) config.scene_path = serverConfig.scene_path
    if (serverConfig.browser_type) config.browser_type = serverConfig.browser_type
    if (serverConfig.headless !== undefined) config.headless = serverConfig.headless
  } catch (e) {
    configError.value = e instanceof Error ? e.message : String(e)
    console.error('Failed to load record config:', e)
  }
})

async function startRecord() {
  if (!config.url) return
  recording.value = true
  progress.value = 0
  result.value = null
  logs.value = []

  try {
    const recordConfig: RecordConfig = {
      url: config.url,
      output_path: config.output_path || '',
      duration: config.duration,
      fps: config.fps,
      canvas_selector: config.canvas_selector,
      scene_path: config.scene_path,
      format: config.format,
      quality: config.quality,
    }

    // 启动录制（立即返回）
    const startRes = await api.startRecord(recordConfig)
    if (!startRes.success) {
      result.value = startRes
      recording.value = false
      return
    }

    // 轮询状态直到完成
    let pollCount = 0
    const maxPolls = Math.ceil(config.duration * 2) + 30
    while (pollCount < maxPolls) {
      await new Promise(r => setTimeout(r, 1000))
      pollCount++
      const status = await api.getRecordStatus()
      progress.value = Math.min(status.progress || (pollCount / maxPolls * 100), 100)

      // 实时更新日志
      if (status.logs) {
        logs.value = status.logs
      }

      if (!status.recording) {
        result.value = {
          success: status.success ?? false,
          message: status.message || '录制完成',
          output_path: status.output_path || null,
          total_frames: status.total_frames || 0,
          duration: status.duration || 0,
          source_fps: status.source_fps || 0,
          output_fps: status.output_fps || 0,
          file_size_mb: status.file_size_mb || 0,
        }
        break
      }
    }
  } catch (e) {
    result.value = {
      success: false,
      message: '录制失败: ' + (e instanceof Error ? e.message : String(e)),
      output_path: null,
      total_frames: 0,
      duration: 0,
      source_fps: 0,
      output_fps: 0,
      file_size_mb: 0,
    }
  } finally {
    recording.value = false
    progress.value = 100
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
.record-log {
  max-height: 300px;
  overflow-y: auto;
  background: #0d1117;
  border-radius: 6px;
  padding: 12px;
  margin-top: 12px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.5;
}
.log-line {
  color: #8b949e;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
