<template>
  <div>
    <div class="pipeline-header">
      <div>
        <h2 class="page-title">流水线控制台</h2>
        <p class="section-intro">点击节点，在右侧完成输入查看、输入修改、节点执行、输出修订和按反馈重生成。</p>
      </div>
      <div v-if="activeTask" class="pipeline-header__meta">
        <span class="badge" :class="statusBadgeClass(activeTask.status)">{{ statusLabel(activeTask.status) }}</span>
        <span class="compact-meta">{{ activeTask.title || activeTask.content.slice(0, 28) }}</span>
      </div>
    </div>

    <div class="pipeline-workbench">
      <section class="pipeline-canvas card">
        <div class="card-header">
          <h3>节点视图</h3>
          <span class="compact-meta">
            {{ activeTask ? `任务 ${activeTask.id}` : '尚未创建任务' }}
          </span>
        </div>
        <PipelineGraph
          :agents="agentDefs"
          :knowledge-requirements="knowledgeRequirements"
          :messages="activeTask?.messages ?? []"
          :active-agent="activeAgentName"
          :selected-node="selectedNodeName"
          :token-usage-by-step="activeTask?.token_usage_by_step"
          @select-node="selectNode"
        />
      </section>

      <aside class="pipeline-panel card">
        <div class="card-header">
          <div>
            <h3>{{ selectedStepLabel }}</h3>
            <div class="compact-meta">{{ selectedStepName }}</div>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            <span class="badge" :class="selectedStatusBadgeClass">{{ selectedStatusText }}</span>
            <span v-if="selectedTokenUsage > 0" class="tag">{{ formatTokenCount(selectedTokenUsage) }} tokens</span>
          </div>
        </div>

        <template v-if="!activeTask">
          <div class="stack-tight">
            <section class="node-section node-section--summary">
              <div class="node-section__header">
                <h4>节点资源</h4>
                <span class="compact-meta">执行前可见的知识与工具</span>
              </div>
              <div class="resource-grid">
                <div class="resource-block">
                  <div class="resource-block__label">知识库输入</div>
                  <div v-if="selectedKnowledgeCategories.length || selectedKnowledgeTags.length" class="resource-chip-list">
                    <span
                      v-for="category in selectedKnowledgeCategories"
                      :key="`create-category-${category}`"
                      class="tag tag-subtle"
                    >
                      分类 · {{ category }}
                    </span>
                    <span
                      v-for="tag in selectedKnowledgeTags"
                      :key="`create-tag-${tag}`"
                      class="tag tag-accent tag-subtle"
                    >
                      标签 · {{ tag }}
                    </span>
                  </div>
                  <div v-if="selectedKnowledgeEntries.length" class="resource-knowledge-list">
                    <div
                      v-for="entry in selectedKnowledgeEntries"
                      :key="`create-entry-${entry.id}`"
                      class="resource-knowledge-item"
                    >
                      <div class="resource-knowledge-item__title">{{ entry.title }}</div>
                      <div class="compact-meta">{{ entry.category }} · {{ entry.source }}</div>
                    </div>
                  </div>
                  <div
                    v-if="!selectedKnowledgeCategories.length && !selectedKnowledgeTags.length && selectedKnowledgeEntries.length"
                    class="compact-meta"
                  >
                    当前节点未声明筛选条件，将读取全部知识库条目。
                  </div>
                  <div
                    v-else-if="!selectedKnowledgeCategories.length && !selectedKnowledgeTags.length && !selectedKnowledgeEntries.length"
                    class="compact-meta"
                  >
                    当前节点未声明额外知识库筛选条件。
                  </div>
                </div>

                <div class="resource-block">
                  <div class="resource-block__label">可调用工具</div>
                  <div v-if="selectedTools.length" class="resource-tool-list">
                    <div v-for="tool in selectedTools" :key="`create-tool-${tool.name}`" class="resource-tool-item">
                      <div class="resource-tool-item__title">{{ tool.name }}</div>
                      <div class="compact-meta">{{ tool.description || '未提供工具说明' }}</div>
                    </div>
                  </div>
                  <div v-else class="compact-meta">当前节点没有额外工具。</div>
                </div>
              </div>
            </section>

            <div class="form-group">
              <label>任务原始输入</label>
              <textarea
                v-model="newTaskContent"
                class="form-textarea"
                rows="6"
                placeholder="输入故事目标、风格约束、角色要求等。"
              />
            </div>
            <div class="form-group">
              <label>从当前节点开始</label>
              <div class="compact-meta">
                当前将从 {{ selectedStepLabel }} 开始；如果不是 A 节点，需要补齐依赖输出。
              </div>
            </div>
            <div
              v-for="depIdx in selectedPrevStepIndices"
              :key="`create-${depIdx}`"
              class="form-group"
            >
              <label>{{ pipelineSteps[depIdx]?.label }} 输出</label>
              <textarea
                v-model="stepInputs[String(depIdx)]"
                class="form-textarea"
                rows="5"
                :placeholder="`请输入 ${pipelineSteps[depIdx]?.label} 的输出`"
              />
            </div>
            <button class="btn btn-primary" :disabled="creating" @click="createTaskFromSelectedNode">
              {{ creating ? '创建中...' : `从 ${selectedStepLabel} 创建任务` }}
            </button>
          </div>
        </template>

        <template v-else>
          <div class="stack-tight">
            <section class="node-section node-section--summary">
              <div class="node-section__header">
                <h4>节点资源</h4>
                <span class="compact-meta">本节点会读取的知识库和可调用工具</span>
              </div>
              <div class="resource-grid">
                <div class="resource-block">
                  <div class="resource-block__label">知识库输入</div>
                  <div v-if="selectedKnowledgeCategories.length || selectedKnowledgeTags.length" class="resource-chip-list">
                    <span
                      v-for="category in selectedKnowledgeCategories"
                      :key="`category-${category}`"
                      class="tag tag-subtle"
                    >
                      分类 · {{ category }}
                    </span>
                    <span
                      v-for="tag in selectedKnowledgeTags"
                      :key="`tag-${tag}`"
                      class="tag tag-accent tag-subtle"
                    >
                      标签 · {{ tag }}
                    </span>
                  </div>
                  <div v-if="selectedKnowledgeEntries.length" class="resource-knowledge-list">
                    <div
                      v-for="entry in selectedKnowledgeEntries"
                      :key="entry.id"
                      class="resource-knowledge-item"
                    >
                      <div class="resource-knowledge-item__title">{{ entry.title }}</div>
                      <div class="compact-meta">{{ entry.category }} · {{ entry.source }}</div>
                    </div>
                  </div>
                  <div
                    v-if="!selectedKnowledgeCategories.length && !selectedKnowledgeTags.length && selectedKnowledgeEntries.length"
                    class="compact-meta"
                  >
                    当前节点未声明筛选条件，将读取全部知识库条目。
                  </div>
                  <div
                    v-else-if="!selectedKnowledgeCategories.length && !selectedKnowledgeTags.length && !selectedKnowledgeEntries.length"
                    class="compact-meta"
                  >
                    当前节点未声明额外知识库筛选条件。
                  </div>
                </div>

                <div class="resource-block">
                  <div class="resource-block__label">可调用工具</div>
                  <div v-if="selectedTools.length" class="resource-tool-list">
                    <div v-for="tool in selectedTools" :key="tool.name" class="resource-tool-item">
                      <div class="resource-tool-item__title">{{ tool.name }}</div>
                      <div class="compact-meta">{{ tool.description || '未提供工具说明' }}</div>
                    </div>
                  </div>
                  <div v-else class="compact-meta">当前节点没有额外工具。</div>
                </div>
              </div>
            </section>

            <section class="node-section">
              <div class="node-section__header">
                <h4>节点输入</h4>
                <span class="compact-meta">{{ selectedStepIndex === 0 ? '原始任务输入' : '来自上游节点' }}</span>
              </div>

              <div v-if="selectedStepIndex === 0" class="form-group">
                <label>任务原始输入</label>
                <textarea
                  v-model="taskContentDraft"
                  class="form-textarea"
                  rows="6"
                  placeholder="请输入任务描述"
                />
                <div class="node-actions">
                  <button class="btn btn-sm btn-primary" @click="saveTaskContent">保存输入</button>
                </div>
              </div>

              <template v-else>
                <details class="details-panel" open>
                  <summary>
                    <span>查看组合输入</span>
                    <span class="summary-chevron">▶</span>
                  </summary>
                  <div class="details-panel__body">
                    <pre class="node-preview">{{ selectedEffectiveInput }}</pre>
                  </div>
                </details>

                <div
                  v-for="depIdx in selectedPrevStepIndices"
                  :key="`dep-${depIdx}`"
                  class="form-group"
                >
                  <label>{{ pipelineSteps[depIdx]?.label }} 输出</label>
                  <textarea
                    :value="getDependencyDraft(depIdx)"
                    class="form-textarea"
                    rows="5"
                    @input="setDependencyDraft(depIdx, ($event.target as HTMLTextAreaElement).value)"
                  />
                  <div class="node-actions">
                    <button class="btn btn-sm btn-primary" @click="saveDependencyOutput(depIdx)">保存为上游输入</button>
                  </div>
                </div>
              </template>
            </section>

            <section class="node-section">
              <div class="node-section__header">
                <h4>节点输出</h4>
                <span class="compact-meta">
                  {{ isSelectedCompleted ? '可直接编辑' : '节点未完成，暂无输出' }}
                </span>
              </div>
              <textarea
                v-model="outputDraft"
                class="form-textarea"
                rows="8"
                :disabled="!isSelectedCompleted"
                :placeholder="isSelectedCompleted ? '编辑该节点输出' : '节点完成后会在这里显示输出'"
              />
              <div v-if="isSelectedCompleted" class="node-actions">
                <button class="btn btn-sm btn-primary" @click="saveSelectedOutput">保存输出</button>
              </div>
            </section>

            <section class="node-section">
              <div class="node-section__header">
                <h4>节点操作</h4>
                <span class="compact-meta">执行、终止或按反馈重生成当前节点</span>
              </div>
              <div class="node-actions node-actions--wrap">
                <button
                  v-if="canRunSelectedNode"
                  class="btn btn-primary"
                  :disabled="runningStep"
                  @click="runSelectedNode"
                >
                  {{ runningStep ? '执行中...' : '执行节点' }}
                </button>
                <button
                  v-if="canCancelSelectedNode"
                  class="btn btn-danger"
                  @click="cancelTask"
                >
                  终止节点
                </button>
              </div>
            </section>

            <section v-if="isSelectedCompleted" class="node-section">
              <div class="node-section__header">
                <h4>反馈重生成</h4>
                <span class="compact-meta">仅从当前节点重新开始，后续节点结果会失效</span>
              </div>
              <textarea
                v-model="revisionDraft"
                class="form-textarea"
                rows="4"
                placeholder="例如：减少旁白，增强冲突，对白更口语化。"
              />
              <div class="node-actions">
                <button
                  class="btn btn-primary"
                  :disabled="runningStep || !revisionDraft.trim()"
                  @click="reviseSelectedNode"
                >
                  按反馈重生成
                </button>
              </div>
            </section>

            <details class="details-panel">
              <summary>
                <span>节点消息与调试信息</span>
                <span class="summary-chevron">▶</span>
              </summary>
              <div class="details-panel__body">
                <div v-if="selectedMessages.length === 0" class="compact-meta">当前节点暂无消息。</div>
                <div v-else class="stack-tight">
                  <div v-for="message in selectedMessages" :key="message.id" class="node-message">
                    <div class="node-message__meta">
                      <span>{{ message.type }}</span>
                      <span>{{ message.sender }} → {{ message.receiver }}</span>
                    </div>
                    <pre class="node-preview">{{ message.content }}</pre>
                  </div>
                </div>
              </div>
            </details>
          </div>
        </template>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import PipelineGraph from '../components/PipelineGraph.vue'
import { PIPELINE_STEPS } from '../constants/pipeline'
import type { AgentInfo, AgentKnowledgeRequirements, AgentToolInfo, Task, TaskMessage } from '../types'
import { formatTokenCount, statusBadgeClass, statusLabel } from '../utils/taskDisplay'

const agentDefs = ref<AgentInfo[]>([])
const knowledgeRequirements = ref<AgentKnowledgeRequirements[]>([])
const activeTask = ref<Task | null>(null)
const selectedNodeName = ref(PIPELINE_STEPS[0]?.name ?? 'outline_writer')
const newTaskContent = ref('')
const stepInputs = ref<Record<string, string>>({})
const taskContentDraft = ref('')
const outputDraft = ref('')
const revisionDraft = ref('')
const dependencyDrafts = ref<Record<string, string>>({})
const creating = ref(false)
const runningStep = ref(false)

const pipelineSteps = PIPELINE_STEPS

const selectedStepIndex = computed(() =>
  Math.max(0, pipelineSteps.findIndex(step => step.name === selectedNodeName.value)),
)

const selectedStep = computed(() => pipelineSteps[selectedStepIndex.value] ?? pipelineSteps[0]!)
const selectedStepLabel = computed(() => selectedStep.value.label)
const selectedStepName = computed(() => selectedStep.value.name)
const selectedAgent = computed(() =>
  agentDefs.value.find(agent => agent.name === selectedStepName.value) ?? null,
)
const selectedKnowledgeRequirement = computed(() =>
  knowledgeRequirements.value.find(item => item.agent === selectedStepName.value) ?? null,
)
const selectedKnowledgeCategories = computed(() => selectedKnowledgeRequirement.value?.categories ?? [])
const selectedKnowledgeTags = computed(() => selectedKnowledgeRequirement.value?.tags ?? [])
const selectedKnowledgeEntries = computed(() => selectedKnowledgeRequirement.value?.entries ?? [])
const selectedTools = computed<AgentToolInfo[]>(() => selectedAgent.value?.tools ?? [])

const selectedPrevStepIndices = computed(() =>
  (selectedStep.value.deps ?? [])
    .map(name => pipelineSteps.findIndex(step => step.name === name))
    .filter(index => index >= 0),
)

const activeAgentName = computed(() => {
  if (!activeTask.value || activeTask.value.status !== 'running') return ''
  return pipelineSteps[activeTask.value.current_step]?.name ?? ''
})

function isStepCompleted(task: Task | null, stepIndex: number): boolean {
  if (!task) return false
  return stepIndex < task.current_step || (task.status === 'completed' && stepIndex === task.current_step)
}

const isSelectedCompleted = computed(() => isStepCompleted(activeTask.value, selectedStepIndex.value))

const selectedStatusText = computed(() => {
  if (!activeTask.value) return '未创建'
  if (activeTask.value.status === 'running' && activeTask.value.current_step === selectedStepIndex.value) return '运行中'
  if (isSelectedCompleted.value) return '已完成'
  if (activeTask.value.current_step === selectedStepIndex.value) return '待执行'
  if (selectedStepIndex.value > activeTask.value.current_step) return '等待上游'
  return '已完成'
})

const selectedStatusBadgeClass = computed(() => {
  if (!activeTask.value) return 'badge-muted'
  if (activeTask.value.status === 'running' && activeTask.value.current_step === selectedStepIndex.value) return 'badge-warning'
  if (activeTask.value.errors.length > 0 && activeTask.value.current_step === selectedStepIndex.value) return 'badge-danger'
  if (isSelectedCompleted.value) return 'badge-success'
  return 'badge-muted'
})

const selectedTokenUsage = computed(() =>
  activeTask.value?.token_usage_by_step?.[String(selectedStepIndex.value)]?.total_tokens ?? 0,
)

const canRunSelectedNode = computed(() =>
  !!activeTask.value &&
  activeTask.value.current_step === selectedStepIndex.value &&
  activeTask.value.status !== 'running' &&
  activeTask.value.status !== 'completed',
)

const canCancelSelectedNode = computed(() =>
  !!activeTask.value &&
  activeTask.value.current_step === selectedStepIndex.value &&
  activeTask.value.status === 'running',
)

const selectedMessages = computed<TaskMessage[]>(() => {
  if (!activeTask.value) return []
  const nodeName = selectedStepName.value
  return activeTask.value.messages.filter(
    message => message.sender === nodeName || message.receiver === nodeName,
  )
})

const selectedEffectiveInput = computed(() => {
  if (!activeTask.value) return ''
  const parts: string[] = []
  if (activeTask.value.content) {
    parts.push(`【用户输入】\n${activeTask.value.content}`)
  }
  for (const depIdx of selectedPrevStepIndices.value) {
    const depName = pipelineSteps[depIdx]?.name
    const depLabel = pipelineSteps[depIdx]?.label
    const depOutput = activeTask.value.step_results[String(depIdx)] || ''
    if (depName && depOutput) {
      parts.push(`【${depLabel}】\n${depOutput}`)
    }
  }
  return parts.join('\n\n')
})

function selectNode(nodeName: string) {
  selectedNodeName.value = nodeName
}

function syncDrafts() {
  if (!activeTask.value) {
    taskContentDraft.value = newTaskContent.value
    outputDraft.value = ''
    revisionDraft.value = ''
    dependencyDrafts.value = {}
    return
  }
  taskContentDraft.value = activeTask.value.content
  outputDraft.value = activeTask.value.step_results[String(selectedStepIndex.value)] || ''
  revisionDraft.value = ''
  const nextDrafts: Record<string, string> = {}
  for (const depIdx of selectedPrevStepIndices.value) {
    nextDrafts[String(depIdx)] = activeTask.value.step_results[String(depIdx)] || ''
  }
  dependencyDrafts.value = nextDrafts
}

watch([activeTask, selectedNodeName], syncDrafts, { immediate: true })

function getDependencyDraft(stepIndex: number): string {
  return dependencyDrafts.value[String(stepIndex)] || ''
}

function setDependencyDraft(stepIndex: number, value: string) {
  dependencyDrafts.value[String(stepIndex)] = value
}

async function createTaskFromSelectedNode() {
  const content = newTaskContent.value.trim()
  if (!content) {
    alert('请先填写任务原始输入')
    return
  }
  for (const depIdx of selectedPrevStepIndices.value) {
    if (!stepInputs.value[String(depIdx)]?.trim()) {
      alert(`请填写「${pipelineSteps[depIdx]?.label}」的输出内容`)
      return
    }
  }
  creating.value = true
  try {
    const task = await api.createTask(content, {
      startStep: selectedStepIndex.value,
      stepInputs: selectedPrevStepIndices.value.length > 0 ? stepInputs.value : undefined,
    })
    activeTask.value = task
    taskContentDraft.value = task.content
  } catch (error) {
    alert('创建任务失败: ' + (error instanceof Error ? error.message : String(error)))
  } finally {
    creating.value = false
  }
}

async function saveTaskContent() {
  if (!activeTask.value) return
  try {
    activeTask.value = await api.updateTaskContent(activeTask.value.id, taskContentDraft.value)
  } catch (error) {
    alert('保存任务输入失败: ' + (error instanceof Error ? error.message : String(error)))
  }
}

async function saveDependencyOutput(stepIndex: number) {
  if (!activeTask.value) return
  try {
    activeTask.value = await api.updateStepResult(
      activeTask.value.id,
      stepIndex,
      getDependencyDraft(stepIndex),
    )
  } catch (error) {
    alert('保存上游输出失败: ' + (error instanceof Error ? error.message : String(error)))
  }
}

async function saveSelectedOutput() {
  if (!activeTask.value) return
  try {
    activeTask.value = await api.updateStepResult(
      activeTask.value.id,
      selectedStepIndex.value,
      outputDraft.value,
    )
  } catch (error) {
    alert('保存节点输出失败: ' + (error instanceof Error ? error.message : String(error)))
  }
}

async function runSelectedNode() {
  if (!activeTask.value) return
  runningStep.value = true
  try {
    const updated = await api.runStep(activeTask.value.id)
    activeTask.value = updated
    await pollTaskUntilIdle(updated.id)
  } catch (error) {
    alert('执行节点失败: ' + (error instanceof Error ? error.message : String(error)))
  } finally {
    runningStep.value = false
  }
}

async function reviseSelectedNode() {
  if (!activeTask.value) return
  if (!revisionDraft.value.trim()) {
    alert('请先填写反馈要求')
    return
  }
  runningStep.value = true
  try {
    const updated = await api.reviseStep(activeTask.value.id, selectedStepIndex.value, revisionDraft.value)
    activeTask.value = updated
    await pollTaskUntilIdle(updated.id)
  } catch (error) {
    alert('重生成失败: ' + (error instanceof Error ? error.message : String(error)))
  } finally {
    runningStep.value = false
  }
}

async function cancelTask() {
  if (!activeTask.value) return
  try {
    activeTask.value = await api.cancelTask(activeTask.value.id)
  } catch (error) {
    alert('终止任务失败: ' + (error instanceof Error ? error.message : String(error)))
  }
}

async function pollTaskUntilIdle(taskId: string) {
  while (true) {
    const latest = await api.getTask(taskId)
    activeTask.value = latest
    if (latest.status !== 'running') return
    await new Promise(resolve => setTimeout(resolve, 1200))
  }
}

onMounted(async () => {
  try {
    const [info, requirements] = await Promise.all([
      api.getPipeline(),
      api.getAgentRequirements(),
    ])
    agentDefs.value = info.agents
    knowledgeRequirements.value = requirements
  } catch (error) {
    console.error('Failed to load pipeline info:', error)
  }

  try {
    const tasks = await api.getTasks()
    const lastTask = tasks[tasks.length - 1]
    if (lastTask && ['pending', 'paused', 'running'].includes(lastTask.status)) {
      activeTask.value = lastTask
      selectedNodeName.value = pipelineSteps[lastTask.current_step]?.name ?? selectedNodeName.value
      if (lastTask.status === 'running') {
        await pollTaskUntilIdle(lastTask.id)
      }
    }
  } catch {
    // ignore
  }
})
</script>

<style scoped>
.pipeline-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.pipeline-header__meta {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.pipeline-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(340px, 0.95fr);
  gap: 14px;
  align-items: start;
}

.pipeline-canvas,
.pipeline-panel {
  min-width: 0;
}

.pipeline-panel {
  position: sticky;
  top: 18px;
}

.node-section {
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.015);
}

.node-section__header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 10px;
}

.node-section__header h4 {
  font-size: 13px;
  font-weight: 800;
}

.node-section--summary {
  background:
    linear-gradient(180deg, rgba(247, 99, 12, 0.06), rgba(255, 255, 255, 0.015));
  border-color: rgba(247, 99, 12, 0.14);
}

.resource-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.resource-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.resource-block__label {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #ffb488;
}

.resource-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.resource-tool-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.resource-knowledge-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.resource-knowledge-item {
  padding: 10px 11px;
  border-radius: 12px;
  background: rgba(247, 99, 12, 0.06);
  border: 1px solid rgba(247, 99, 12, 0.14);
}

.resource-knowledge-item__title {
  font-size: 12px;
  font-weight: 800;
  color: var(--text);
  margin-bottom: 2px;
}

.resource-tool-item {
  padding: 10px 11px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
}

.resource-tool-item__title {
  font-size: 12px;
  font-weight: 800;
  color: var(--text);
  margin-bottom: 2px;
}

.node-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  align-items: center;
}

.node-actions--wrap {
  flex-wrap: wrap;
}

.node-preview {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 11px;
  line-height: 1.6;
  color: var(--text-soft);
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px;
}

.node-message {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.node-message__meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 11px;
  color: var(--text-muted);
}

:deep(.tag-subtle) {
  margin-right: 0;
}

@media (max-width: 1180px) {
  .pipeline-workbench {
    grid-template-columns: 1fr;
  }

  .pipeline-panel {
    position: static;
  }
}
</style>
