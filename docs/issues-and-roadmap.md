# WebGalAgent 问题与优化路线图

> 本文档基于项目全面审查，记录当前存在的问题、潜在改进方向和未来功能规划。
>
> 状态标记：`[已修复]` 表示问题已解决，`[待修复]` 表示尚未处理。

---

## 一、当前存在的问题

### 🔴 严重（需尽快修复）

#### 1. ~~API Key 明文泄露到版本控制~~ `[已修复]`

- **位置**: `src/configs/providers.yaml`
- **问题**: API Key 被直接写入 YAML 并提交到 Git 仓库
- **修复措施**（2026-05-12）:
  1. ✅ 使用 `git filter-repo` 从 Git 全部历史中移除 `providers.yaml`
  2. ✅ 将 `providers.yaml` 加入 `.gitignore`
  3. ✅ 创建 `providers.yaml.sample` 作为模板（不含真实 Key），已提交到仓库
  4. ✅ 本地重新创建 `providers.yaml`（Git 不再跟踪）
- **残留风险**: 旧 Key 仍可能存在于已推送到远程的历史或协作者本地克隆中，**务必到 SiliconFlow 控制台轮换 API Key**

#### 2. ~~Provider API 无认证保护~~ `[非问题]`

- **位置**: `src/webgal_agent/api/routes/provider.py`
- **说明**: WebGalAgent 是单用户本地应用，无需鉴权保护

#### 3. ~~Provider API 返回 API Key 明文~~ `[非问题]`

- **位置**: `src/webgal_agent/api/routes/provider.py` 第 23 行
- **说明**: 单用户本地应用，API Key 仅在本机可见，无需脱敏

#### 4. ~~TaskManager 不支持并发任务~~ `[非问题]` ✅

- **位置**: `src/webgal_agent/api/task_manager.py`
- **说明**: TaskManager 设计为强制单任务执行，这是有意为之的设计决策。同一时间只允许一个任务执行，避免 LLM API 资源竞争和上下文混乱
- **已优化**（2026-05-12）: 移除了不必要的并发数据结构（`_background_tasks` 集合、`_running_tasks` 字典），简化为单任务引用 `_running_task`；`run_step()` 增加全局运行检查，其他任务运行时返回错误提示

#### 5. Agent `run()` 方法完全重复 `[待修复]`

- **位置**:
  - `src/webgal_agent/agents/outline_writer.py` 第 38-56 行
  - `src/webgal_agent/agents/script_writer.py` 第 38-56 行
  - `src/webgal_agent/agents/script_converter.py` 第 38-56 行
- **问题**: 三个 `run()` 方法的代码逐行完全相同，仅类名不同
- **建议**: 提取为基类 `BaseAgent` 的通用 `run()` 方法，子类仅需定义差异化配置

---

### 🟡 中等（应尽快处理）

#### 6. ReadFileTool 路径检查范围过大 `[待修复]`

- **位置**: `src/webgal_agent/tools/file_ops.py` 第 70-87 行
- **问题**: `_allowed_dirs` 包含 `pathlib.Path(".").resolve()` 即当前工作目录，LLM 理论上可读取项目任意文件（包括含 API Key 的 `providers.yaml`）
- **建议**: 收紧允许目录至 `data/` 和游戏输出目录，移除项目根目录

#### 7. PipelineView 轮询不停止 `[待修复]`

- **位置**: `src/frontend/src/views/PipelineView.vue` 第 355-368 行
- **问题**: `pollTask` 使用 `setTimeout` 递归调用但没有清理机制；离开页面再回来可能产生多个轮询链
- **建议**: 添加 `onUnmounted` 钩子清除轮询定时器（参考 `TasksView` 的实现）

#### 8. `_call_llm` 无异常处理和重试 `[待修复]`

- **位置**: `src/webgal_agent/core/agent.py` 第 145-182 行
- **问题**: OpenAI API 调用无 try/except，网络错误、认证错误、限流等直接抛出；`AgentConfig.max_retries` 字段已定义但从未使用
- **建议**: 添加指数退避重试逻辑，利用已有的 `max_retries` 配置

#### 9. `_call_llm_with_tools` 最大轮次边界问题 `[待修复]`

- **位置**: `src/webgal_agent/core/agent.py` 第 366-374 行
- **问题**: 如果 `max_tool_rounds=0`，for 循环不执行，`assistant_msg` 未定义，第 369 行会抛出 `NameError`
- **建议**: 在循环前初始化 `assistant_msg = None` 并添加边界检查

#### 10. API 层缺少统一异常处理 `[待修复]`

- **位置**: `src/webgal_agent/api/app.py`
- **问题**: 未注册全局 exception handler，未捕获异常直接返回 500，可能泄露堆栈信息
- **建议**: 添加 FastAPI `@app.exception_handler` 统一处理，返回结构化错误响应

#### 11. 前端 API 请求无超时 `[待修复]`

- **位置**: `src/frontend/src/api/index.ts`
- **问题**: fetch 请求没有设置超时，LLM 调用可能持续数分钟
- **建议**: 使用 `AbortController` 设置请求超时（如 5 分钟）

#### 12. 模块级全局变量管理单例 `[待修复]`

- **位置**: `src/webgal_agent/api/app.py` 第 19-21 行
- **问题**: 使用模块级全局变量 + 已过时的 `@app.on_event("startup")` 管理单例
- **建议**: 改用 FastAPI 的 `lifespan` 上下文管理器和依赖注入

#### 13. `update_step_result` 只更新第一条匹配消息 `[待修复]`

- **位置**: `src/webgal_agent/api/task_manager.py` 第 624-628 行
- **问题**: 如果同一智能体有多条 RESULT 消息（如重跑），只更新第一条；且直接修改 Pydantic 模型字段绕过验证
- **建议**: 更新最后一条匹配消息，或使用 `model_copy(update=...)` 替代直接赋值

#### 14. AgentState 缺少 CANCELLED 状态 `[待修复]`

- **位置**: `src/webgal_agent/core/agent.py` 第 22-30 行
- **问题**: AgentState 枚举没有 CANCELLED 状态，但 TaskManager 将任务状态设为 `"cancelled"`，语义不一致
- **建议**: 在 AgentState 枚举中添加 CANCELLED 状态

#### 15. `KnowledgeEntry.category` 类型不一致 `[待修复]`

- **位置**: `src/webgal_agent/knowledge/models.py` 第 33 行、`store.py` 第 179 行
- **问题**: 字段类型声明为 `str`，默认值混用枚举和字符串，导致比较行为不一致
- **建议**: 统一使用 `KnowledgeCategory` 枚举类型

---

### 🟢 轻微（可择时处理）

#### 16. `_resolve_game_dir` 逻辑重复 3 次 `[待修复]`

- **位置**: `tools/file_ops.py`、`tools/asset_query.py`、`api/routes/assets.py`
- **建议**: 提取为共享工具函数

#### 17. 前端工具函数和常量重复 `[待修复]`

- `formatTokenCount` 在 `MessageBubble.vue`、`PipelineGraph.vue`、`PipelineView.vue`、`TasksView.vue` 中各定义一次
- `AGENT_LABELS` 在 4 个组件中重复定义
- `pipelineSteps`、`statusBadgeClass`、`statusLabel` 在 2 个视图中重复
- `PipelineView.vue` 和 `TasksView.vue` 有约 80 行完全相同的 CSS
- **建议**: 提取到 `utils/` 和 `composables/` 目录，CSS 使用共享样式文件

#### 18. `_load_prompts` 和 `_load_knowledge_requirements` 重复读取同一文件 `[待修复]`

- **位置**: `src/webgal_agent/api/task_manager.py` 第 144-187 行
- **建议**: 合并为一次读取，缓存结果

#### 19. 每次 `run_step` 都重建所有 Agent `[待修复]`

- **位置**: `src/webgal_agent/api/task_manager.py` 第 527 行
- **建议**: 缓存或复用 Agent 实例

#### 20. `get_workflow_info` 每次调用都构建 Agent `[待修复]`

- **位置**: `src/webgal_agent/api/task_manager.py` 第 671-690 行
- **问题**: 仅用于返回配置信息，却实例化了所有 Agent
- **建议**: 直接从配置中读取信息，无需实例化 Agent

#### 21. 路由直接访问私有属性 `[待修复]`

- `knowledge.py` 第 83 行访问 `tm._knowledge_requirements`
- `task.py` 第 126 行访问 `Path(manager._task_dir)`
- **建议**: 在 TaskManager 上暴露公共属性或方法

#### 22. `InMemoryMemory.get_recent(0)` 返回全部消息 `[待修复]`

- **位置**: `src/webgal_agent/core/memory.py` 第 51 行
- **问题**: `self._messages[-0:]` 返回全部消息而非空列表
- **建议**: 添加 `if n <= 0: return []` 边界检查

#### 23. knowledge reload 返回 count 为字符串 `[待修复]`

- **位置**: `src/webgal_agent/api/routes/knowledge.py` 第 108 行
- **建议**: 返回整数而非 `str(store.count())`

#### 24. 类型安全不足 `[待修复]`

- `_call_llm_with_tools` 使用 `list[Any]` 和 `cast(Any, ...)` 绕过类型检查
- `tool_calls` 属性使用 `type: ignore`
- 前端 `request` 函数抛出通用 Error，无法区分 404/400/500
- **建议**: 引入 OpenAI SDK 的 Message 类型；前端定义 `ApiError` 类

---

## 二、未使用/冗余代码

| 代码 | 位置 | 说明 |
|------|------|------|
| `AppSettings` / `LLMSettings` / `AgentSettings` | `config/settings.py` | 已定义但项目中完全未使用，配置通过 `ProviderConfigManager` 管理 |
| `SharedContext` | `core/context.py` | 已定义但项目中没有任何地方使用 |
| `PipelineWorkflow.execute` | `workflows/pipeline.py` | 生产代码绕过它，由 TaskManager 独立实现步骤执行；仅在测试中使用 |
| `AgentConfig.max_retries` | `core/agent.py` | 已定义但从未使用 |
| `default.yaml` 中旧 agent 名称 | `configs/default.yaml` | 包含 director/writer/artist/reviewer，与实际 outline_writer/script_writer/script_converter 不匹配 |

---

## 三、未来功能与优化方向

### 🚀 高优先级

#### 1. 实时推送（WebSocket / SSE）

- **现状**: 前端使用轮询获取任务状态更新，延迟高、浪费资源
- **方案**: 
  - 后端集成 FastAPI WebSocket 或 SSE 端点
  - TaskManager 在步骤完成/消息更新时推送事件
  - 前端替换轮询为事件监听
- **收益**: 实时反馈、降低服务器负载、更好的用户体验

#### 2. 用户认证与授权（仅多用户部署时需要）

- **现状**: 单用户本地应用，无需鉴权
- **方案**（如未来需要多用户部署）:
  - 添加 JWT 或 Session 认证
  - API Key 存储加密
  - 角色权限控制（管理员/普通用户）
- **收益**: 适合多用户/远程部署场景

#### 3. 并发任务支持（可选）

- **现状**: TaskManager 设计为强制单任务执行，这是有意为之的设计决策
- **方案**（如未来需要支持并发）:
  - TaskManager 使用 `dict[str, Agent]` 替代单例 `_active_agents`
  - 可配置最大并发数
  - 任务队列管理
- **前提**: 需确保 LLM API 配额充足、资源隔离可靠
- **收益**: 提高吞吐量，支持批量生成

#### 4. 测试覆盖率提升

- **现状**: 仅 10 个测试覆盖 core 基础功能
- **方案**:
  - 优先补充：`task_manager.py`（编排核心）、`agent.py`（ReAct 循环）、API 路由
  - 使用 `pytest-asyncio` 测试异步逻辑
  - Mock OpenAI API 响应
  - 目标覆盖率 ≥ 60%
- **收益**: 保障重构安全、防止回归

---

### 📈 中优先级

#### 5. LLM 调用重试与容错

- **现状**: 无重试逻辑，网络波动直接失败
- **方案**:
  - 实现 `tenacity` 或自定义指数退避重试
  - 支持流式响应（Streaming）减少等待时间
  - 请求/响应日志记录
- **收益**: 提高稳定性、便于调试

#### 6. 配置系统重构

- **现状**: `AppSettings` 未使用，`default.yaml` 与代码脱节，路径硬编码
- **方案**:
  - 统一使用 pydantic-settings 管理所有配置
  - 支持 `.env`、环境变量、YAML 多来源
  - 移除硬编码路径，全部可配置化
- **收益**: 配置一致性、部署灵活性

#### 7. 数据库持久化

- **现状**: 全部使用内存 + JSON 文件，任务历史查询效率低
- **方案**:
  - 引入 SQLite（轻量，无需额外服务）或 PostgreSQL
  - 使用 SQLAlchemy 或 Tortoise ORM
  - 迁移现有 JSON 数据
- **收益**: 查询性能、数据完整性、支持复杂统计

#### 8. 代码去重与重构

- 提取 Agent 基类通用 `run()` 方法
- 前端工具函数提取到 `utils/` 和 `composables/`
- 共享 CSS 提取到全局样式
- `_resolve_game_dir` 提取为公共工具
- **收益**: 可维护性、一致性

#### 9. 国际化（i18n）

- **现状**: 前端 UI 文案全部硬编码中文
- **方案**: 使用 `vue-i18n` 支持多语言
- **收益**: 扩大用户群

#### 10. 前端错误边界与用户体验

- 添加 Vue ErrorBoundary 组件
- API 错误统一 Toast 通知
- Loading 骨架屏
- 操作撤销/重做
- **收益**: 更健壮的用户体验

---

### 🔮 远期规划

#### 11. 多工作流支持

- **现状**: 仅 Pipeline（顺序）一种工作流
- **方案**:
  - 支持分支/条件工作流
  - 人工审核节点（Human-in-the-loop）
  - 工作流可视化编辑器
- **收益**: 灵活编排、质量控制

#### 12. 插件/工具市场

- 支持自定义 Tool 注册
- 工具发现与组合
- 社区贡献工具包
- **收益**: 可扩展性

#### 13. 多模型对比与 A/B 测试

- 同一任务使用不同模型执行
- 结果对比与评分
- 最优模型推荐
- **收益**: 输出质量优化

#### 14. Docker 化部署

- 提供 Dockerfile 和 docker-compose.yml
- 一键部署，环境一致
- 支持 GPU 加速配置
- **收益**: 部署便利性

#### 15. 生成历史版本管理

- 任务步骤结果支持版本对比
- Diff 视图
- 回滚到历史版本
- **收益**: 迭代控制、质量追溯

#### 16. 性能监控与告警

- Token 消耗趋势图
- LLM 响应延迟监控
- 异常调用告警
- **收益**: 运营可视化和成本控制

#### 17. 知识库增强

- 支持向量数据库（如 ChromaDB）语义检索
- 自动从游戏资源提取知识
- 知识条目版本管理
- **收益**: 知识检索精度

#### 18. 素材管理增强

- 素材预览缩略图
- 标签与分类系统
- 素材使用频率统计
- **收益**: 素材利用效率

---

## 四、问题优先级矩阵

| 优先级 | 问题 | 影响范围 | 修复难度 |
|--------|------|----------|----------|
| P0 | ~~API Key 泄露~~ ✅ | 安全 | 低 |
| P0 | ~~API 无认证~~ ✅ | 安全 | — |
| P1 | 并发任务支持（可选） | 功能 | 中 |
| P1 | Agent run() 重复 | 可维护性 | 低 |
| P1 | 轮询不停止 | 可靠性 | 低 |
| P1 | LLM 调用无重试 | 稳定性 | 低 |
| P2 | 类型安全 | 代码质量 | 中 |
| P2 | 统一异常处理 | 稳定性 | 低 |
| P2 | 代码去重 | 可维护性 | 中 |
| P2 | 测试覆盖率 | 质量 | 高 |
| P3 | 未使用代码清理 | 整洁度 | 低 |
| P3 | CSS 重复 | 可维护性 | 低 |
| P3 | 配置系统统一 | 架构 | 中 |

---

*最后更新: 2026-05-12 | 变更：问题 #1 API Key 泄露已修复*
