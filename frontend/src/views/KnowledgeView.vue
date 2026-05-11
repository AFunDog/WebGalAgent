<template>
  <div>
    <h2 class="page-title">知识库</h2>

    <!-- 智能体知识需求 -->
    <div v-if="requirements.length > 0" class="card" style="margin-bottom:20px">
      <div class="card-header"><h3>智能体知识需求</h3></div>
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
              无筛选 — 加载全部知识
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;align-items:center">
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
      <span style="margin-left:auto;color:var(--text-muted);font-size:13px">
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

    <!-- 知识条目列表 -->
    <div style="margin-top:16px">
      <div v-if="entries.length === 0" class="empty-state">
        <p>暂无知识条目</p>
      </div>
      <div v-for="entry in entries" :key="entry.id" class="card">
        <div class="card-header">
          <h3>{{ entry.title }}</h3>
          <div>
            <span class="tag tag-clickable" @click="filterByCategory(entry.category)">
              {{ entry.category }}
            </span>
            <span
              v-for="tag in entry.tags"
              :key="tag"
              class="tag tag-clickable tag-accent"
              :class="{ 'tag-active': filterTags.includes(tag) }"
              @click="filterByTag(tag)"
            >{{ tag }}</span>
          </div>
        </div>
        <pre style="color:var(--text-muted);font-size:13px;white-space:pre-wrap;font-family:inherit;margin:0">{{ entry.body }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api'
import type { KnowledgeEntry, AgentKnowledgeRequirements } from '../types'

const AGENT_LABELS: Record<string, string> = {
  outline_writer: 'A: 剧本大纲编写',
  script_writer: 'B: 章节剧本生成',
  script_converter: 'C: WebGal 脚本转换',
}

const entries = ref<KnowledgeEntry[]>([])
const categories = ref<string[]>([])
const allTags = ref<string[]>([])
const requirements = ref<AgentKnowledgeRequirements[]>([])

const filterCategory = ref('')
const filterKeyword = ref('')
const filterTags = ref<string[]>([])

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
