// ===== API helpers =====
const API = {
  async get(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
    return r.json();
  },
  async post(url, body) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
    return r.json();
  },
  async put(url, body) {
    const r = await fetch(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
    return r.json();
  },
};

// ===== Icons (inline SVG) =====
const ICONS = {
  knowledge: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`,
  workflow: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="5" cy="6" r="3"/><circle cx="19" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><path d="M8 6h8M12 9v6M9 8l3 7M15 8l-3 7"/></svg>`,
  task: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`,
  send: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>`,
  settings: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`,
};

// ===== App State =====
let currentPage = "knowledge";
let knowledgeEntries = [];
let categories = [];
let allTags = [];
let agentRequirements = [];
let tasks = [];
let workflowInfo = null;
let providerData = null;
let providerPresets = null;
let filterCategory = "";
let filterKeyword = "";
let filterTags = [];
let editingAgent = null; // which agent is being edited in the modal

// ===== Page: Knowledge =====
async function loadKnowledge() {
  try {
    const params = new URLSearchParams();
    if (filterCategory) params.set("category", filterCategory);
    if (filterKeyword) params.set("keyword", filterKeyword);
    if (filterTags.length > 0) params.set("tags", filterTags.join(","));
    const qs = params.toString();
    knowledgeEntries = await API.get("/api/knowledge" + (qs ? "?" + qs : ""));
    categories = await API.get("/api/knowledge/categories");
    allTags = await API.get("/api/knowledge/tags");
    agentRequirements = await API.get("/api/knowledge/agent-requirements");
  } catch (e) {
    console.error("Failed to load knowledge:", e);
  }
  render();
}

// ===== Page: Workflow =====
async function loadWorkflows() {
  try {
    workflowInfo = await API.get("/api/workflows/pipeline");
  } catch (e) {
    console.error("Failed to load workflows:", e);
  }
  render();
}

// ===== Page: Tasks =====
// 跟踪当前活跃的轮询定时器
let activePolls = {};

async function loadTasks() {
  try {
    tasks = await API.get("/api/tasks");
  } catch (e) {
    console.error("Failed to load tasks:", e);
  }
  render();
  // 对进行中的任务启动轮询
  tasks.forEach(t => {
    if ((t.status === "running" || t.status === "pending") && !activePolls[t.id]) {
      pollTaskStatus(t.id);
    }
  });
}

async function createTask(content) {
  try {
    const task = await API.post("/api/tasks", { content });
    // 创建后立即切换到任务列表并开始轮询
    await loadTasks();
    pollTaskStatus(task.id);
  } catch (e) {
    alert("创建任务失败: " + e.message);
  }
}

function pollTaskStatus(taskId) {
  // 避免重复轮询
  if (activePolls[taskId]) return;

  let attempts = 0;
  const maxAttempts = 600; // 最多轮询 10 分钟（每秒一次）
  const timer = setInterval(async () => {
    attempts++;
    try {
      const task = await API.get("/api/tasks/" + taskId);
      // 局部更新列表中对应任务，避免全量 render 导致页面跳顶
      const idx = tasks.findIndex(t => t.id === taskId);
      if (idx !== -1) {
        tasks[idx] = task;
        updateTaskCard(task);
      }
      if (task.status !== "running" && task.status !== "pending") {
        clearInterval(timer);
        delete activePolls[taskId];
      }
    } catch (e) {
      console.error("轮询任务状态失败:", e);
    }
    if (attempts >= maxAttempts) {
      clearInterval(timer);
      delete activePolls[taskId];
    }
  }, 1000);
  activePolls[taskId] = timer;
}

function updateTaskCard(task) {
  const card = document.getElementById("task-card-" + task.id);
  if (!card) return;

  const statusClass = task.status === "completed" ? "success" : task.status === "running" ? "warning" : task.status === "failed" ? "danger" : "muted";
  const badge = card.querySelector(".badge");
  if (badge) {
    badge.className = "badge badge-" + statusClass;
    badge.textContent = task.status;
  }

  // 更新消息列表
  const msgContainer = card.querySelector(".task-messages");
  if (msgContainer) {
    msgContainer.innerHTML = task.messages.map(m => `
      <div class="msg-bubble ${m.type}">
        <div><strong>${esc(m.sender)}</strong> → <strong>${esc(m.receiver)}</strong></div>
        <div style="white-space:pre-wrap;margin-top:4px">${esc(m.content)}</div>
        <div class="msg-meta">${esc(m.type)} · ${new Date(m.created_at).toLocaleTimeString()}</div>
      </div>`).join("");
  }

  // 更新错误
  const errEl = card.querySelector(".task-errors");
  if (errEl) {
    errEl.textContent = task.errors.length ? task.errors.join("; ") : "";
  }
}

// ===== Page: Providers =====
async function loadProviders() {
  try {
    providerData = await API.get("/api/providers");
    providerPresets = await API.get("/api/providers/presets");
  } catch (e) {
    console.error("Failed to load providers:", e);
  }
  render();
}

async function saveProvider(agentName) {
  const form = document.getElementById("provider-form");
  if (!form) return;

  const body = {
    provider: form.provider.value,
    model: form.model.value,
    base_url: form.base_url.value,
    api_key: form.api_key.value,
    temperature: parseFloat(form.temperature.value),
    max_tokens: parseInt(form.max_tokens.value),
  };

  try {
    if (agentName === "__defaults__") {
      await API.put("/api/providers", body);
    } else {
      await API.put("/api/providers/" + agentName, body);
    }
    editingAgent = null;
    await loadProviders();
  } catch (e) {
    alert("保存失败: " + e.message);
  }
}

function applyPreset(presetName) {
  const form = document.getElementById("provider-form");
  if (!form || !providerPresets || !providerPresets[presetName]) return;

  const preset = providerPresets[presetName];
  form.provider.value = preset.provider || presetName;
  form.base_url.value = preset.base_url || "";
}

// ===== Routing =====
function navigate(page) {
  currentPage = page;
  editingAgent = null;
  if (page === "knowledge") loadKnowledge();
  else if (page === "workflows") loadWorkflows();
  else if (page === "tasks") loadTasks();
  else if (page === "providers") loadProviders();
}

// ===== Render =====
function render() {
  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="app-layout">
      ${renderTopbar()}
      ${renderSidebar()}
      <main class="main">
        ${currentPage === "knowledge" ? renderKnowledgePage() : ""}
        ${currentPage === "workflows" ? renderWorkflowsPage() : ""}
        ${currentPage === "tasks" ? renderTasksPage() : ""}
        ${currentPage === "providers" ? renderProvidersPage() : ""}
      </main>
    </div>
    ${editingAgent !== null ? renderProviderModal() : ""}`;
  bindEvents();
}

function renderTopbar() {
  return `<div class="topbar"><h1>WebGalAgent</h1><span style="color:var(--text-muted);font-size:13px">多智能体协作工作流</span></div>`;
}

function renderSidebar() {
  const items = [
    { id: "knowledge", label: "知识库", icon: ICONS.knowledge },
    { id: "workflows", label: "工作流", icon: ICONS.workflow },
    { id: "tasks", label: "任务执行", icon: ICONS.task },
    { id: "providers", label: "提供商配置", icon: ICONS.settings },
  ];
  return `
    <nav class="sidebar">
      ${items.map(i => `<a href="#" data-nav="${i.id}" class="${currentPage === i.id ? "active" : ""}">${i.icon}<span>${i.label}</span></a>`).join("")}
    </nav>`;
}

function renderKnowledgePage() {
  // Agent labels for display
  const agentLabels = {
    outline_writer: "A: 剧本大纲编写",
    script_writer: "B: 章节剧本生成",
    script_converter: "C: WebGal 脚本转换",
  };

  // Agent knowledge requirements section
  const requirementsHtml = agentRequirements.length === 0
    ? ""
    : `
    <div class="card" style="margin-bottom:20px">
      <div class="card-header"><h3>智能体知识需求</h3></div>
      <div class="agent-req-grid">
        ${agentRequirements.map(r => `
          <div class="agent-req-item">
            <div class="agent-req-name">${esc(agentLabels[r.agent] || r.agent)}</div>
            <div class="agent-req-details">
              ${r.categories.length ? `<div><span class="agent-req-label">分类:</span> ${r.categories.map(c => `<span class="tag tag-clickable" data-action="filter-by-category" data-category="${esc(c)}">${esc(c)}</span>`).join("")}</div>` : ""}
              ${r.tags.length ? `<div><span class="agent-req-label">标签:</span> ${r.tags.map(t => `<span class="tag tag-clickable tag-accent" data-action="filter-by-tag" data-tag="${esc(t)}">${esc(t)}</span>`).join("")}</div>` : ""}
              ${!r.categories.length && !r.tags.length ? `<div style="color:var(--text-muted);font-size:12px">无筛选 — 加载全部知识</div>` : ""}
            </div>
          </div>`).join("")}
      </div>
    </div>`;

  // Tag filter chips
  const tagChipsHtml = allTags.length === 0
    ? ""
    : `
    <div class="tag-filter-row">
      <span class="tag-filter-label">标签:</span>
      ${allTags.map(t => `<span class="tag tag-clickable ${filterTags.includes(t) ? "tag-active" : ""}" data-action="toggle-tag" data-tag="${esc(t)}">${esc(t)}</span>`).join("")}
    </div>`;

  const entriesHtml = knowledgeEntries.length === 0
    ? `<div class="empty-state"><p>暂无知识条目</p></div>`
    : knowledgeEntries.map(e => `
      <div class="card">
        <div class="card-header">
          <h3>${esc(e.title)}</h3>
          <div>
            <span class="tag tag-clickable" data-action="filter-by-category" data-category="${esc(e.category)}">${esc(e.category)}</span>
            ${e.tags.map(t => `<span class="tag tag-clickable tag-accent ${filterTags.includes(t) ? "tag-active" : ""}" data-action="filter-by-tag" data-tag="${esc(t)}">${esc(t)}</span>`).join("")}
          </div>
        </div>
        <pre style="color:var(--text-muted);font-size:13px;white-space:pre-wrap;font-family:inherit;margin:0">${esc(e.body)}</pre>
      </div>`).join("");

  return `
    <h2 class="page-title">知识库</h2>
    ${requirementsHtml}
    <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;align-items:center">
      <select id="filter-category" class="form-select" style="width:auto">
        <option value="">全部分类</option>
        ${categories.map(c => `<option value="${esc(c)}" ${filterCategory === c ? "selected" : ""}>${esc(c)}</option>`).join("")}
      </select>
      <input id="filter-keyword" class="form-input" style="width:200px" placeholder="搜索关键词..." value="${esc(filterKeyword)}" />
      <button class="btn btn-primary btn-sm" data-action="filter-knowledge">筛选</button>
      <button class="btn btn-ghost btn-sm" data-action="clear-filter">重置</button>
      <span style="margin-left:auto;color:var(--text-muted);font-size:13px">${knowledgeEntries.length} 条记录</span>
    </div>
    ${tagChipsHtml}
    <div style="margin-top:16px">
    ${entriesHtml}
    </div>`;
}

function renderWorkflowsPage() {
  const agentSteps = workflowInfo
    ? workflowInfo.agents.map((a, i) => {
        const stepLabels = ["A: 编写剧本大纲", "B: 生成章节剧本", "C: 转换为 WebGal 脚本"];
        const arrow = i < workflowInfo.agents.length - 1 ? `<div style="text-align:center;color:var(--text-muted);font-size:24px;padding:4px 0">↓</div>` : "";
        return `
          <div class="card">
            <div class="card-header">
              <h3>${stepLabels[i] || a.name}</h3>
              <div>
                <span class="badge badge-muted">${esc(a.name)}</span>
                <span class="tag" style="margin-left:4px">${esc(a.provider)}/${esc(a.model)}</span>
              </div>
            </div>
            <p style="color:var(--text-muted);font-size:13px">${esc(a.description)}</p>
          </div>
          ${arrow}`;
      }).join("")
    : `<div class="empty-state"><p>加载中...</p></div>`;

  return `
    <h2 class="page-title">工作流</h2>
    <div class="card" style="margin-bottom:20px">
      <p style="color:var(--text-muted);font-size:14px">${workflowInfo ? esc(workflowInfo.description) : ""}</p>
    </div>
    ${agentSteps}
    <div class="card" style="margin-top:20px">
      <div class="card-header"><h3>智能体状态</h3></div>
      <div class="table-wrap">
        <table id="agent-status-table">
          <thead><tr><th>名称</th><th>描述</th><th>提供商</th><th>模型</th><th>状态</th></tr></thead>
          <tbody><tr><td colspan="5" style="color:var(--text-muted)">加载中...</td></tr></tbody>
        </table>
      </div>
    </div>`;
}

function renderTasksPage() {
  const tasksHtml = tasks.length === 0
    ? `<div class="empty-state"><p>暂无任务，在下方创建新任务</p></div>`
    : tasks.slice().reverse().map(t => {
        const statusClass = t.status === "completed" ? "success" : t.status === "running" ? "warning" : t.status === "failed" ? "danger" : "muted";
        return `
        <div class="card" id="task-card-${esc(t.id)}">
          <div class="card-header">
            <h3>${esc(t.content.slice(0, 80))}</h3>
            <span class="badge badge-${statusClass}">${esc(t.status)}</span>
          </div>
          <p style="color:var(--text-muted);font-size:12px">ID: ${esc(t.id)} · 创建时间: ${new Date(t.created_at).toLocaleString()}</p>
          ${t.errors.length ? `<p class="task-errors" style="color:var(--danger);font-size:12px;margin-top:4px">${esc(t.errors.join("; "))}</p>` : '<p class="task-errors" style="display:none"></p>'}
          <div class="task-messages" style="margin-top:12px">
            ${t.messages.map(m => `
              <div class="msg-bubble ${m.type}">
                <div><strong>${esc(m.sender)}</strong> → <strong>${esc(m.receiver)}</strong></div>
                <div style="white-space:pre-wrap;margin-top:4px">${esc(m.content)}</div>
                <div class="msg-meta">${esc(m.type)} · ${new Date(m.created_at).toLocaleTimeString()}</div>
              </div>`).join("")}
          </div>
        </div>`;
      }).join("");

  return `
    <h2 class="page-title">任务执行</h2>
    <div class="card" style="margin-bottom:24px">
      <div class="card-header"><h3>创建新任务</h3></div>
      <div class="form-group">
        <label>任务内容</label>
        <textarea id="task-content" class="form-textarea" placeholder="请输入任务描述..."></textarea>
      </div>
      <button class="btn btn-primary" data-action="create-task">${ICONS.send} 执行任务</button>
    </div>
    ${tasksHtml}`;
}

function renderProvidersPage() {
  if (!providerData) {
    return `<h2 class="page-title">提供商配置</h2><div class="empty-state"><p>加载中...</p></div>`;
  }

  const defaults = providerData.defaults || {};
  const agents = providerData.agents || {};

  // Defaults card
  const defaultsCard = `
    <div class="card">
      <div class="card-header">
        <h3>默认配置</h3>
        <button class="btn btn-ghost btn-sm" data-action="edit-provider" data-agent="__defaults__">编辑</button>
      </div>
      <div class="provider-info">
        <div class="provider-field"><span class="provider-label">提供商</span><span>${esc(defaults.provider)}</span></div>
        <div class="provider-field"><span class="provider-label">模型</span><span>${esc(defaults.model)}</span></div>
        <div class="provider-field"><span class="provider-label">Base URL</span><span class="provider-url">${esc(defaults.base_url)}</span></div>
        <div class="provider-field"><span class="provider-label">API Key</span><span>${defaults.api_key ? "••••••••" : "未设置"}</span></div>
        <div class="provider-field"><span class="provider-label">Temperature</span><span>${defaults.temperature}</span></div>
        <div class="provider-field"><span class="provider-label">Max Tokens</span><span>${defaults.max_tokens}</span></div>
      </div>
    </div>`;

  // Per-agent cards
  const agentLabels = {
    outline_writer: "A: 剧本大纲编写",
    script_writer: "B: 章节剧本生成",
    script_converter: "C: WebGal 脚本转换",
  };

  const agentCards = Object.entries(agents).map(([name, cfg]) => {
    const label = agentLabels[name] || name;
    return `
    <div class="card">
      <div class="card-header">
        <h3>${esc(label)}</h3>
        <div style="display:flex;gap:6px;align-items:center">
          <span class="tag">${esc(cfg.provider)}/${esc(cfg.model)}</span>
          <button class="btn btn-ghost btn-sm" data-action="edit-provider" data-agent="${esc(name)}">编辑</button>
        </div>
      </div>
      <div class="provider-info">
        <div class="provider-field"><span class="provider-label">提供商</span><span>${esc(cfg.provider)}</span></div>
        <div class="provider-field"><span class="provider-label">模型</span><span>${esc(cfg.model)}</span></div>
        <div class="provider-field"><span class="provider-label">Base URL</span><span class="provider-url">${esc(cfg.base_url)}</span></div>
        <div class="provider-field"><span class="provider-label">API Key</span><span>${cfg.api_key ? "••••••••" : "未设置"}</span></div>
        <div class="provider-field"><span class="provider-label">Temperature</span><span>${cfg.temperature}</span></div>
        <div class="provider-field"><span class="provider-label">Max Tokens</span><span>${cfg.max_tokens}</span></div>
      </div>
    </div>`;
  }).join("");

  return `
    <h2 class="page-title">提供商配置</h2>
    <p style="color:var(--text-muted);font-size:14px;margin-bottom:20px">配置每个智能体使用的 LLM 提供商、模型和参数。未单独配置的智能体将使用默认配置。</p>
    ${defaultsCard}
    <h3 style="margin:24px 0 16px;font-size:16px">智能体配置</h3>
    ${agentCards}`;
}

function renderProviderModal() {
  const isDefaults = editingAgent === "__defaults__";
  const cfg = isDefaults
    ? (providerData?.defaults || {})
    : (providerData?.agents?.[editingAgent] || providerData?.defaults || {});

  const agentLabels = {
    __defaults__: "默认配置",
    outline_writer: "A: 剧本大纲编写",
    script_writer: "B: 章节剧本生成",
    script_converter: "C: WebGal 脚本转换",
  };

  const presetOptions = providerPresets
    ? Object.keys(providerPresets).map(k => `<option value="${esc(k)}">${esc(k)}</option>`).join("")
    : "";

  return `
    <div class="modal-overlay" data-action="close-modal">
      <div class="modal">
        <h2>编辑 — ${esc(agentLabels[editingAgent] || editingAgent)}</h2>

        <div class="form-group">
          <label>快捷预设</label>
          <div style="display:flex;gap:8px">
            <select id="preset-select" class="form-select" style="flex:1">
              <option value="">选择预设...</option>
              ${presetOptions}
            </select>
            <button class="btn btn-ghost btn-sm" data-action="apply-preset">应用</button>
          </div>
        </div>

        <form id="provider-form">
          <div class="grid-2">
            <div class="form-group">
              <label>提供商 (Provider)</label>
              <input name="provider" class="form-input" value="${esc(cfg.provider || "")}" />
            </div>
            <div class="form-group">
              <label>模型 (Model)</label>
              <input name="model" class="form-input" value="${esc(cfg.model || "")}" />
            </div>
          </div>
          <div class="form-group">
            <label>Base URL</label>
            <input name="base_url" class="form-input" value="${esc(cfg.base_url || "")}" />
          </div>
          <div class="form-group">
            <label>API Key</label>
            <input name="api_key" class="form-input" type="password" value="${esc(cfg.api_key || "")}" placeholder="sk-..." />
          </div>
          <div class="grid-2">
            <div class="form-group">
              <label>Temperature</label>
              <input name="temperature" class="form-input" type="number" step="0.1" min="0" max="2" value="${cfg.temperature ?? 0.7}" />
            </div>
            <div class="form-group">
              <label>Max Tokens</label>
              <input name="max_tokens" class="form-input" type="number" min="1" value="${cfg.max_tokens ?? 4096}" />
            </div>
          </div>
        </form>

        <div class="modal-actions">
          <button class="btn btn-ghost" data-action="close-modal">取消</button>
          <button class="btn btn-primary" data-action="save-provider">保存</button>
        </div>
      </div>
    </div>`;
}

function esc(str) {
  const d = document.createElement("div");
  d.textContent = str || "";
  return d.innerHTML;
}

// ===== Event Binding =====
function bindEvents() {
  // Navigation
  document.querySelectorAll("[data-nav]").forEach(el => {
    el.onclick = e => { e.preventDefault(); navigate(el.dataset.nav); };
  });

  // Knowledge filter
  document.querySelector("[data-action='filter-knowledge']")?.addEventListener("click", () => {
    filterCategory = document.getElementById("filter-category")?.value || "";
    filterKeyword = document.getElementById("filter-keyword")?.value || "";
    loadKnowledge();
  });

  // Clear knowledge filter
  document.querySelector("[data-action='clear-filter']")?.addEventListener("click", () => {
    filterCategory = "";
    filterKeyword = "";
    filterTags = [];
    loadKnowledge();
  });

  // Filter by clicking category tag
  document.querySelectorAll("[data-action='filter-by-category']").forEach(el => {
    el.onclick = e => {
      e.preventDefault();
      filterCategory = el.dataset.category || "";
      loadKnowledge();
    };
  });

  // Filter by clicking tag in agent requirements or entry card
  document.querySelectorAll("[data-action='filter-by-tag']").forEach(el => {
    el.onclick = e => {
      e.preventDefault();
      const tag = el.dataset.tag;
      if (tag && !filterTags.includes(tag)) {
        filterTags = [tag];
        loadKnowledge();
      }
    };
  });

  // Toggle tag chips in filter row
  document.querySelectorAll("[data-action='toggle-tag']").forEach(el => {
    el.onclick = e => {
      e.preventDefault();
      const tag = el.dataset.tag;
      if (!tag) return;
      if (filterTags.includes(tag)) {
        filterTags = filterTags.filter(t => t !== tag);
      } else {
        filterTags.push(tag);
      }
      loadKnowledge();
    };
  });

  // Task actions
  document.querySelector("[data-action='create-task']")?.addEventListener("click", () => {
    const content = document.getElementById("task-content")?.value || "";
    if (!content.trim()) { alert("请输入任务内容"); return; }
    createTask(content);
  });

  // Edit provider
  document.querySelectorAll("[data-action='edit-provider']").forEach(el => {
    el.onclick = e => {
      e.stopPropagation();
      editingAgent = el.dataset.agent;
      render();
    };
  });

  // Save provider
  document.querySelector("[data-action='save-provider']")?.addEventListener("click", () => {
    saveProvider(editingAgent);
  });

  // Close modal
  document.querySelectorAll("[data-action='close-modal']").forEach(el => {
    el.onclick = e => {
      if (e.target === el || el.classList.contains("btn-ghost")) {
        editingAgent = null;
        render();
      }
    };
  });

  // Apply preset
  document.querySelector("[data-action='apply-preset']")?.addEventListener("click", () => {
    const select = document.getElementById("preset-select");
    if (select?.value) {
      applyPreset(select.value);
    }
  });

  // Load agent status on workflow page
  if (currentPage === "workflows") {
    loadAgentStatus();
  }
}

async function loadAgentStatus() {
  try {
    const agents = await API.get("/api/workflows/agents/status");
    const tbody = document.querySelector("#agent-status-table tbody");
    if (tbody) {
      tbody.innerHTML = agents.map(a => `
        <tr>
          <td><strong>${esc(a.name)}</strong></td>
          <td style="color:var(--text-muted)">${esc(a.description)}</td>
          <td><span class="tag">${esc(a.provider || "-")}</span></td>
          <td>${esc(a.model || "-")}</td>
          <td><span class="badge badge-${a.state === 'idle' ? 'muted' : 'success'}">${esc(a.state)}</span></td>
        </tr>`).join("");
    }
  } catch (e) {
    console.error("Failed to load agent status:", e);
  }
}

// ===== Init =====
document.addEventListener("DOMContentLoaded", () => {
  navigate("knowledge");
});
