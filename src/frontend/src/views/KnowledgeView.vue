<template>
  <div>
    <h2 class="page-title">知识库</h2>

    <!-- 智能体知识需求：保留系统视角，方便核对知识路由 -->
    <details v-if="requirements.length > 0" class="details-panel" style="margin-bottom:12px">
      <summary>
        <span>智能体知识需求</span>
        <span class="summary-chevron">▶</span>
      </summary>
      <div class="details-panel__body">
        <div class="agent-req-grid">
          <div v-for="req in requirements" :key="req.agent" class="agent-req-item">
            <div class="agent-req-name">{{ AGENT_LABELS[req.agent] ?? req.agent }}</div>
            <div class="agent-req-details">
              <div v-if="req.categories.length">
                <span class="agent-req-label">分类:</span>
                <span
                  v-for="cat in req.categories"
                  :key="cat"
                  class="tag tag-clickable"
                  @click="filterByCategory(cat)"
                >{{ cat }}</span>
              </div>
              <div v-if="req.tags.length">
                <span class="agent-req-label">标签:</span>
                <span
                  v-for="tag in req.tags"
                  :key="tag"
                  class="tag tag-clickable tag-accent"
                  @click="filterByTag(tag)"
                >{{ tag }}</span>
              </div>
              <div
                v-if="!req.categories.length && !req.tags.length"
                style="color:var(--text-muted);font-size:12px"
              >
                无筛选，加载全部知识
              </div>
            </div>
          </div>
        </div>
      </div>
    </details>

    <!-- 筛选工具栏：保留底层 category/tag 过滤，但主浏览方式改为人类可读分组 -->
    <div class="compact-toolbar">
      <select v-model="filterCategory" class="form-select" style="width:auto">
        <option value="">全部分类</option>
        <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
      </select>
      <input
        v-model="filterKeyword"
        class="form-input"
        style="width:200px"
        placeholder="搜索关键词..."
        @keyup.enter="loadEntries"
      />
      <button class="btn btn-primary btn-sm" @click="loadEntries">筛选</button>
      <button class="btn btn-ghost btn-sm" @click="clearFilter">重置</button>
      <span style="margin-left:auto" class="compact-meta">
        {{ entries.length }} 条记录
      </span>
    </div>

    <!-- 标签筛选 -->
    <div v-if="allTags.length > 0" class="tag-filter-row">
      <span class="tag-filter-label">标签:</span>
      <span
        v-for="tag in allTags"
        :key="tag"
        class="tag tag-clickable"
        :class="{ 'tag-accent': filterTags.includes(tag), 'tag-active': filterTags.includes(tag) }"
        @click="toggleTag(tag)"
      >{{ tag }}</span>
    </div>

    <!-- 顶层导航：角色 / 世界观 / 技能 -->
    <div class="knowledge-tabs">
      <button
        v-for="section in visibleSections"
        :key="section.key"
        class="knowledge-tab"
        :class="{ active: activeSection === section.key }"
        @click="activeSection = section.key"
      >
        <span>{{ section.label }}</span>
        <span class="knowledge-tab-count">{{ section.count }}</span>
      </button>
    </div>

    <!-- 分组后的知识条目 -->
    <div style="margin-top:16px">
      <div v-if="entries.length === 0" class="empty-state">
        <p>暂无知识条目</p>
      </div>

      <!-- 角色：按角色目录聚合角色信息与立绘资料 -->
      <div v-else-if="activeSection === 'character'" class="knowledge-section-stack">
        <div v-if="characterGroups.length === 0" class="empty-state">
          <p>当前筛选下没有角色资料</p>
        </div>
        <div v-for="group in characterGroups" :key="group.key" class="knowledge-group">
          <div class="knowledge-group-header">
            <div>
              <h3>{{ group.label }}</h3>
              <p>{{ group.entries.length }} 份文档</p>
            </div>
          </div>
          <div class="knowledge-group-body">
            <div
              v-for="entry in group.entries"
              :key="entry.id"
              class="knowledge-card"
              @click="toggle(entry.id)"
            >
              <div class="knowledge-card-header">
                <div class="knowledge-card-title">
                  <span class="knowledge-expand-icon" :class="{ expanded: expandedIds.has(entry.id) }">▶</span>
                  <h3>{{ getEntryDisplayTitle(entry) }}</h3>
                </div>
                <div class="knowledge-card-meta">
                  <span class="tag tag-clickable" @click.stop="filterByCategory(entry.category)">
                    {{ entry.category }}
                  </span>
                  <span
                    v-for="tag in entry.tags"
                    :key="tag"
                    class="tag tag-clickable tag-accent"
                    :class="{ 'tag-active': filterTags.includes(tag) }"
                    @click.stop="filterByTag(tag)"
                  >{{ tag }}</span>
                </div>
              </div>
              <div class="knowledge-card-subtitle">{{ entry.title }}</div>
              <div v-if="!expandedIds.has(entry.id)" class="knowledge-card-preview">
                {{ getPreview(entry.body) }}
              </div>
              <div v-else class="knowledge-card-body">
                <div class="knowledge-card-source">{{ entry.source }}</div>
                <pre>{{ entry.body }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 世界观 / 技能：按文档展示 -->
      <div v-else class="knowledge-section-stack">
        <div v-if="activeEntries.length === 0" class="empty-state">
          <p>当前筛选下没有相关文档</p>
        </div>
        <div
          v-for="entry in activeEntries"
          :key="entry.id"
          class="knowledge-card"
          @click="toggle(entry.id)"
        >
          <div class="knowledge-card-header">
            <div class="knowledge-card-title">
              <span class="knowledge-expand-icon" :class="{ expanded: expandedIds.has(entry.id) }">▶</span>
              <h3>{{ entry.title }}</h3>
            </div>
            <div class="knowledge-card-meta">
              <span class="tag tag-clickable" @click.stop="filterByCategory(entry.category)">
                {{ entry.category }}
              </span>
              <span
                v-for="tag in entry.tags"
                :key="tag"
                class="tag tag-clickable tag-accent"
                :class="{ 'tag-active': filterTags.includes(tag) }"
                @click.stop="filterByTag(tag)"
              >{{ tag }}</span>
            </div>
          </div>
          <div class="knowledge-card-subtitle">{{ getEntrySubtitle(entry) }}</div>
          <div v-if="!expandedIds.has(entry.id)" class="knowledge-card-preview">
            {{ getPreview(entry.body) }}
          </div>
          <div v-else class="knowledge-card-body">
            <div class="knowledge-card-source">{{ entry.source }}</div>
            <pre>{{ entry.body }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import type { AgentKnowledgeRequirements, KnowledgeEntry } from '../types'

type KnowledgeSectionKey = 'character' | 'world' | 'skill' | 'other'

const AGENT_LABELS: Record<string, string> = {
  outline_writer: 'A: 剧本大纲编写',
  script_writer: 'B: 章节剧本生成',
  script_converter: 'C: WebGal 脚本转换',
}

const SECTION_LABELS: Record<KnowledgeSectionKey, string> = {
  character: '角色',
  world: '世界观',
  skill: '技能',
  other: '其他',
}

const entries = ref<KnowledgeEntry[]>([])
const categories = ref<string[]>([])
const allTags = ref<string[]>([])
const requirements = ref<AgentKnowledgeRequirements[]>([])

const filterCategory = ref('')
const filterKeyword = ref('')
const filterTags = ref<string[]>([])
const expandedIds = ref<Set<string>>(new Set())
const activeSection = ref<KnowledgeSectionKey>('character')

function toggle(id: string) {
  const next = new Set(expandedIds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  expandedIds.value = next
}

function getPreview(body: string): string {
  const firstLine = body.split('\n').find(line => line.trim()) ?? ''
  return firstLine.length > 80 ? firstLine.slice(0, 80) + '…' : firstLine
}

function getSectionKey(entry: KnowledgeEntry): KnowledgeSectionKey {
  const normalized = entry.source.replace(/\\/g, '/')
  if (normalized.startsWith('characters/')) return 'character'
  if (normalized.startsWith('settings/')) return 'world'
  if (normalized.startsWith('skills/')) return 'skill'
  if (entry.category === 'character' || entry.category === 'world' || entry.category === 'skill') {
    return entry.category
  }
  return 'other'
}

function getCharacterGroupKey(entry: KnowledgeEntry): string {
  const normalized = entry.source.replace(/\\/g, '/')
  const parts = normalized.split('/')
  if (parts[0] === 'characters' && parts.length >= 3) {
    return parts[1] ?? entry.title
  }
  if (parts[0] === 'characters') {
    const leaf = parts[parts.length - 1] ?? entry.source
    return leaf.replace(/\.md(\.sample)?$/, '')
  }
  return entry.title
}

function getEntryDisplayTitle(entry: KnowledgeEntry): string {
  const normalized = entry.source.replace(/\\/g, '/')
  if (normalized.endsWith('/profile.md')) return '角色信息'
  if (normalized.endsWith('/expression_motion.md')) return '立绘表情动作'
  return entry.title
}

function getEntrySubtitle(entry: KnowledgeEntry): string {
  const normalized = entry.source.replace(/\\/g, '/')
  const parts = normalized.split('/')
  return parts[parts.length - 1] || entry.source
}

const entriesBySection = computed(() => {
  const grouped: Record<KnowledgeSectionKey, KnowledgeEntry[]> = {
    character: [],
    world: [],
    skill: [],
    other: [],
  }
  for (const entry of entries.value) {
    grouped[getSectionKey(entry)].push(entry)
  }
  return grouped
})

const visibleSections = computed(() => {
  const ordered: KnowledgeSectionKey[] = ['character', 'world', 'skill', 'other']
  const sections = ordered
    .map(key => ({
      key,
      label: SECTION_LABELS[key],
      count: entriesBySection.value[key].length,
    }))
    .filter(section => section.count > 0)

  const firstSection = sections[0]
  if (!sections.some(section => section.key === activeSection.value) && firstSection) {
    activeSection.value = firstSection.key
  }
  return sections
})

const activeEntries = computed(() => entriesBySection.value[activeSection.value] ?? [])

const characterGroups = computed(() => {
  const groups = new Map<string, KnowledgeEntry[]>()
  for (const entry of entriesBySection.value.character) {
    const key = getCharacterGroupKey(entry)
    if (!groups.has(key)) {
      groups.set(key, [])
    }
    groups.get(key)!.push(entry)
  }

  return Array.from(groups.entries())
    .map(([key, groupEntries]) => ({
      key,
      label: key,
      entries: [...groupEntries].sort((a, b) => getEntryDisplayTitle(a).localeCompare(getEntryDisplayTitle(b), 'zh-CN')),
    }))
    .sort((a, b) => a.label.localeCompare(b.label, 'zh-CN'))
})

async function loadEntries() {
  try {
    entries.value = await api.getKnowledge({
      category: filterCategory.value || undefined,
      keyword: filterKeyword.value || undefined,
      tags: filterTags.value.length > 0 ? filterTags.value : undefined,
    })
  } catch (e) {
    console.error('Failed to load knowledge:', e)
  }
}

async function loadAll() {
  try {
    const [ent, cats, tags, reqs] = await Promise.all([
      api.getKnowledge(),
      api.getCategories(),
      api.getTags(),
      api.getAgentRequirements(),
    ])
    entries.value = ent
    categories.value = cats
    allTags.value = tags
    requirements.value = reqs
  } catch (e) {
    console.error('Failed to load knowledge:', e)
  }
}

function clearFilter() {
  filterCategory.value = ''
  filterKeyword.value = ''
  filterTags.value = []
  loadEntries()
}

function filterByCategory(cat: string) {
  filterCategory.value = cat
  loadEntries()
}

function filterByTag(tag: string) {
  if (!filterTags.value.includes(tag)) {
    filterTags.value = [tag]
    loadEntries()
  }
}

function toggleTag(tag: string) {
  const idx = filterTags.value.indexOf(tag)
  if (idx !== -1) {
    filterTags.value.splice(idx, 1)
  } else {
    filterTags.value.push(tag)
  }
  loadEntries()
}

onMounted(loadAll)
</script>

<style scoped>
  .tag-filter-row {
    display: flex;
    flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-bottom: 8px;
}

.tag-filter-label {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
  margin-right: 4px;
}

.knowledge-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
    margin-top: 10px;
  }

.knowledge-tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.15s;
}

.knowledge-tab:hover {
  background: var(--bg-input);
  color: var(--text);
}

.knowledge-tab.active {
  background: rgba(99, 102, 241, 0.16);
  color: var(--primary-hover);
  border-color: rgba(99, 102, 241, 0.45);
}

.knowledge-tab-count {
  min-width: 20px;
  padding: 0 6px;
  background: rgba(148, 163, 184, 0.16);
  border-radius: 999px;
  font-size: 12px;
  line-height: 20px;
}

.knowledge-tab.active .knowledge-tab-count {
  background: rgba(99, 102, 241, 0.22);
}

.knowledge-section-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.knowledge-group {
  background: rgba(30, 41, 59, 0.42);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
}

.knowledge-group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.knowledge-group-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.knowledge-group-header p {
  font-size: 12px;
  color: var(--text-muted);
}

.knowledge-group-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.knowledge-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 14px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.15s;
}

.knowledge-card:hover {
  border-color: var(--primary);
}

.knowledge-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.knowledge-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.knowledge-card-title h3 {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.knowledge-expand-icon {
  font-size: 10px;
  color: var(--text-muted);
  transition: transform 0.2s;
  flex-shrink: 0;
}

.knowledge-expand-icon.expanded {
  transform: rotate(90deg);
}

.knowledge-card-meta {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.knowledge-card-subtitle {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.knowledge-card-preview {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.knowledge-card-body {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}

.knowledge-card-source {
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--text-muted);
  word-break: break-all;
}

.knowledge-card-body pre {
  color: var(--text-muted);
  font-size: 12px;
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
  line-height: 1.6;
}

.agent-req-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}

.agent-req-item {
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 12px;
}

.agent-req-name {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text);
}

.agent-req-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.agent-req-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
  margin-right: 4px;
}
</style>
