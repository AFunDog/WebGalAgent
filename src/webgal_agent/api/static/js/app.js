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
};

// ===== Icons (inline SVG) =====
const ICONS = {
  knowledge: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`,
  workflow: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="5" cy="6" r="3"/><circle cx="19" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><path d="M8 6h8M12 9v6M9 8l3 7M15 8l-3 7"/></svg>`,
  task: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`,
  send: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>`,
};

// ===== App State =====
let currentPage = "knowledge";
let knowledgeEntries = [];
let categories = [];
let tasks = [];
let workflows = [];
let filterCategory = "";
let filterKeyword = "";

// ===== Page: Knowledge =====
async function loadKnowledge() {
  try {
    const params = new URLSearchParams();
    if (filterCategory) params.set("category", filterCategory);
    if (filterKeyword) params.set("keyword", filterKeyword);
    const qs = params.toString();
    knowledgeEntries = await API.get("/api/knowledge" + (qs ? "?" + qs : ""));
    categories = await API.get("/api/knowledge/categories");
  } catch (e) {
    console.error("Failed to load knowledge:", e);
  }
  render();
}

async function reloadKnowledge() {
  try {
    await API.post("/api/knowledge/reload", {});
    await loadKnowledge();
  } catch (e) {
    alert("重载失败: " + e.message);
  }
}

// ===== Page: Workflow =====
async function loadWorkflows() {
  try {
    workflows = await API.get("/api/workflows");
  } catch (e) {
    console.error("Failed to load workflows:", e);
  }
  render();
}

// ===== Page: Tasks =====
async function loadTasks() {
  try {
    tasks = await API.get("/api/tasks");
  } catch (e) {
    console.error("Failed to load tasks:", e);
  }
  render();
}

async function createTask(content, workflow) {
  try {
    await API.post("/api/tasks", { content, workflow });
    await loadTasks();
  } catch (e) {
    alert("创建任务失败: " + e.message);
  }
}

// ===== Routing =====
function navigate(page) {
  currentPage = page;
  if (page === "knowledge") loadKnowledge();
  else if (page === "workflows") loadWorkflows();
  else if (page === "tasks") loadTasks();
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
      </main>
    </div>`;
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
  ];
  return `
    <nav class="sidebar">
      ${items.map(i => `<a href="#" data-nav="${i.id}" class="${currentPage === i.id ? "active" : ""}">${i.icon}<span>${i.label}</span></a>`).join("")}
    </nav>`;
}

function renderKnowledgePage() {
  const entriesHtml = knowledgeEntries.length === 0
    ? `<div class="empty-state"><p>暂无知识条目</p></div>`
    : knowledgeEntries.map(e => `
      <div class="card">
        <div class="card-header">
          <h3>${esc(e.title)}</h3>
          <div>
            <span class="tag">${esc(e.category)}</span>
            ${e.tags.map(t => `<span class="tag">${esc(t)}</span>`).join("")}
          </div>
        </div>
        <pre style="color:var(--text-muted);font-size:13px;white-space:pre-wrap;font-family:inherit;margin:0">${esc(e.body)}</pre>
      </div>`).join("");

  return `
    <h2 class="page-title">知识库</h2>
    <div style="display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap;align-items:center">
      <select id="filter-category" class="form-select" style="width:auto">
        <option value="">全部分类</option>
        ${categories.map(c => `<option value="${esc(c)}" ${filterCategory === c ? "selected" : ""}>${esc(c)}</option>`).join("")}
      </select>
      <input id="filter-keyword" class="form-input" style="width:200px" placeholder="搜索关键词..." value="${esc(filterKeyword)}" />
      <button class="btn btn-primary btn-sm" data-action="filter-knowledge">筛选</button>
      <span style="margin-left:auto;color:var(--text-muted);font-size:13px">${knowledgeEntries.length} 条记录</span>
    </div>
    ${entriesHtml}`;
}

function renderWorkflowsPage() {
  return `
    <h2 class="page-title">工作流</h2>
    <div class="grid-2">
      ${workflows.map(w => `
        <div class="card">
          <div class="card-header">
            <h3>${w === "sequential" ? "顺序流水线" : w === "debate" ? "辩论迭代" : esc(w)}</h3>
            <span class="badge badge-muted">${esc(w)}</span>
          </div>
          <p style="color:var(--text-muted);font-size:13px">${
            w === "sequential"
              ? "智能体按固定顺序依次执行，前一个的输出作为后一个的输入"
              : "创作者与审核员交替执行，直到质量评分达到阈值"
          }</p>
        </div>`).join("")}
    </div>
    <div class="card" style="margin-top:20px">
      <div class="card-header"><h3>智能体状态</h3></div>
      <div class="table-wrap">
        <table id="agent-status-table">
          <thead><tr><th>名称</th><th>描述</th><th>状态</th></tr></thead>
          <tbody><tr><td colspan="3" style="color:var(--text-muted)">加载中...</td></tr></tbody>
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
        <div class="card">
          <div class="card-header">
            <h3>${esc(t.content.slice(0, 80))}</h3>
            <div>
              <span class="badge badge-${statusClass}">${esc(t.status)}</span>
              <span class="tag">${esc(t.workflow)}</span>
            </div>
          </div>
          <p style="color:var(--text-muted);font-size:12px">ID: ${esc(t.id)} · 创建时间: ${new Date(t.created_at).toLocaleString()}</p>
          ${t.errors.length ? `<p style="color:var(--danger);font-size:12px;margin-top:4px">${esc(t.errors.join("; "))}</p>` : ""}
          <div style="margin-top:12px">
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
      <div class="form-group">
        <label>工作流类型</label>
        <select id="task-workflow" class="form-select">
          <option value="sequential">顺序流水线</option>
          <option value="debate">辩论迭代</option>
        </select>
      </div>
      <button class="btn btn-primary" data-action="create-task">${ICONS.send} 执行任务</button>
    </div>
    ${tasksHtml}`;
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

  // Task actions
  document.querySelector("[data-action='create-task']")?.addEventListener("click", () => {
    const content = document.getElementById("task-content")?.value || "";
    const workflow = document.getElementById("task-workflow")?.value || "sequential";
    if (!content.trim()) { alert("请输入任务内容"); return; }
    createTask(content, workflow);
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
