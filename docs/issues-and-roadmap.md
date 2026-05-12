# WebGalAgent 问题与优化路线图

> 本文档基于项目全面审查，记录当前存在的问题、潜在改进方向和未来功能规划。

---

## 一、当前存在的问题

### 🔴 严重（需尽快修复）

#### 1. ReadFileTool 路径检查范围过大

- **位置**: `src/webgal_agent/tools/file_ops.py` 第 70-87 行
- **问题**: `_allowed_dirs` 包含 `pathlib.Path(".").resolve()` 即当前工作目录，LLM 理论上可读取项目任意文件（包括含 API Key 的 `providers.yaml`）
- **建议**: 收紧允许目录至 `data/` 和游戏输出目录，移除项目根目录

#### 2. API 调用超时硬编码

- **位置**: `src/webgal_agent/core/agent.py` `_get_client()` 方法
- **问题**: `AsyncOpenAI(timeout=180.0)` 对所有智能体使用同一硬编码超时，无法按智能体或模型调整。`script_converter` 等重型任务频繁超时
- **建议**: 将 timeout 提升为 `ProviderConfig` / `AgentConfig` 可配置字段

---

### 🟡 中等（应尽快处理）

#### 3. `_call_llm` / `_call_llm_with_tools` 无异常处理和重试

- **位置**: `src/webgal_agent/core/agent.py` 两个 LLM 调用方法
- **问题**: OpenAI API 调用无 try/except，网络错误、认证错误、限流等直接抛出；`AgentConfig.max_retries` 字段已定义但从未使用
- **建议**: 添加指数退避重试逻辑，利用已有的 `max_retries` 配置

#### 4. `_call_llm_with_tools` 最大轮次边界问题

- **位置**: `src/webgal_agent/core/agent.py` 第 382-390 行
- **问题**: 如果 `max_tool_rounds=0`，for 循环不执行，`assistant_msg` 未定义，会抛出 `NameError`
- **建议**: 在循环前初始化 `assistant_msg = None` 并添加边界检查

#### 5. API 层缺少统一异常处理

- **位置**: `src/webgal_agent/api/app.py`
- **问题**: 未注册全局 exception handler，未捕获异常直接返回 500，可能泄露堆栈信息
- **建议**: 添加 FastAPI `@app.exception_handler` 统一处理，返回结构化错误响应

#### 6. 前端 API 请求无超时

- **位置**: `src/frontend/src/api/index.ts`
- **问题**: fetch 请求没有设置超时，LLM 调用可能持续数分钟
- **建议**: 使用 `AbortController` 设置请求超时（如 5 分钟）

#### 7. 模块级全局变量管理单例

- **位置**: `src/webgal_agent/api/app.py` 第 19-21 行
- **问题**: 使用模块级全局变量 + 已过时的 `@app.on_event("startup")` 管理单例
- **建议**: 改用 FastAPI 的 `lifespan` 上下文管理器和依赖注入

#### 8. `update_step_result` 只更新第一条匹配消息

- **位置**: `src/webgal_agent/api/task_manager.py` 第 624-628 行
- **问题**: 如果同一智能体有多条 RESULT 消息（如重跑），只更新第一条；且直接修改 Pydantic 模型字段绕过验证
- **建议**: 更新最后一条匹配消息，或使用 `model_copy(update=...)` 替代直接赋值

#### 9. AgentState 缺少 CANCELLED 状态

- **位置**: `src/webgal_agent/core/agent.py` 第 22-30 行
- **问题**: AgentState 枚举没有 CANCELLED 状态，但 TaskManager 将任务状态设为 `"cancelled"`，语义不一致
- **建议**: 在 AgentState 枚举中添加 CANCELLED 状态

#### 10. `KnowledgeEntry.category` 类型不一致

- **位置**: `src/webgal_agent/knowledge/models.py` 第 33 行、`store.py` 第 179 行
- **问题**: 字段类型声明为 `str`，默认值混用枚举和字符串，导致比较行为不一致
- **建议**: 统一使用 `KnowledgeCategory` 枚举类型

#### 11. `ReadModelTool` 和 `AssetQueryTool` 路径解析逻辑重复

- **位置**: `src/webgal_agent/tools/read_model.py` → `resolve_game_dir()`，`src/webgal_agent/tools/asset_query.py` → `_resolve_assets_base_dir()`
- **问题**: 两个工具各自调用 `resolve_game_dir()` 并设置各自的回退默认值，逻辑重复且默认值不一致（`data/assets` vs 直接使用 figure 路径）
- **建议**: 提取共享的 `_resolve_assets_dir()` 到 `_paths.py`，统一回退逻辑

---

### 🟢 轻微（可择时处理）

#### 12. 前端工具函数和常量重复

- `formatTokenCount` 在 `MessageBubble.vue`、`PipelineGraph.vue`、`PipelineView.vue`、`TasksView.vue` 中各定义一次
- `AGENT_LABELS` 在 4 个组件中重复定义
- `pipelineSteps`、`statusBadgeClass`、`statusLabel` 在 2 个视图中重复
- `PipelineView.vue` 和 `TasksView.vue` 有约 80 行完全相同的 CSS
- **建议**: 提取到 `utils/` 和 `composables/` 目录，CSS 使用共享样式文件

#### 13. `_load_prompts` 和 `_load_knowledge_requirements` 重复读取同一文件

- **位置**: `src/webgal_agent/api/task_manager.py` 第 144-187 行
- **建议**: 合并为一次读取，缓存结果

#### 14. 每次 `run_step` 都重建所有 Agent

- **位置**: `src/webgal_agent/api/task_manager.py` 第 527 行
- **建议**: 缓存或复用 Agent 实例

#### 15. `get_workflow_info` 每次调用都构建 Agent

- **位置**: `src/webgal_agent/api/task_manager.py` 第 671-690 行
- **问题**: 仅用于返回配置信息，却实例化了所有 Agent
- **建议**: 直接从配置中读取信息，无需实例化 Agent

#### 16. 路由直接访问私有属性

- `knowledge.py` 第 83 行访问 `tm._knowledge_requirements`
- `task.py` 第 126 行访问 `Path(manager._task_dir)`
- **建议**: 在 TaskManager 上暴露公共属性或方法

#### 17. `InMemoryMemory.get_recent(0)` 返回全部消息

- **位置**: `src/webgal_agent/core/memory.py` 第 51 行
- **问题**: `self._messages[-0:]` 返回全部消息而非空列表
- **建议**: 添加 `if n <= 0: return []` 边界检查

#### 18. knowledge reload 返回 count 为字符串

- **位置**: `src/webgal_agent/api/routes/knowledge.py` 第 108 行
- **建议**: 返回整数而非 `str(store.count())`

#### 19. 类型安全不足

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

## 三、近期变更与进展

### ✅ 已完成 (2026-05)

| 变更 | 说明 |
|------|------|
| `AgentConfig` 新增 `reasoning_effort` 和 `extra_body` | 支持推理模型深度控制和 DeepSeek thinking 模式等非标参数，可通过 `providers.yaml` 按智能体独立配置 |
| `AssetQueryTool` character 查询优化 | character 类型只返回 `model*.json`（立绘模型定义），不再返回纹理 PNG / physics.json / 表情 JSON 等无关文件，大幅减少 token 消耗 |
| `ReadModelTool` 新建 | 专用工具，读取 model.json 仅返回 `motions` 和 `expressions` 列表，供智能体在 `changeFigure` 中准确引用合法的表情/动作参数 |
| 提示词优化 | `script_converter` 新增 `read_model` 工具说明、表情/动作来源工作流、切换频率规则（每 1~2 句对话切换一次）、`-next` 参数使用技巧 |
| `webgal_script_syntax.md` 技巧补充 | Live2D 章节新增 `-next` 参数使用技巧：切换动作/表情时加 `-next` 可不阻塞后续对话 |

### 🔄 待跟进

- **LLM 重试与超时**：`max_retries` 仍未生效，timeout 仍硬编码，需要优先跟进（问题 #2, #3）
- **路径解析统一**：`AssetQueryTool` 和 `ReadModelTool` 的 `resolve_game_dir()` 调用可合并到 `_paths.py`（问题 #11）

---

## 四、未来功能与优化方向

### 🚀 高优先级

#### 1. LLM 调用容错与可观测性

- **现状**: `AgentConfig.max_retries` 已定义但未兑现，timeout 硬编码 180s，无异常重试
- **方案**:
  - 将 `max_retries` 接入 `AsyncOpenAI` 构造函数
  - timeout 提升为 `ProviderConfig` 可配置字段
  - 请求/响应日志记录 Token 用量和延迟
- **收益**: 消除 script_converter 频繁超时问题，提升稳定性

#### 2. 实时推送（WebSocket / SSE）

- **现状**: 前端使用轮询获取任务状态更新，延迟高、浪费资源
- **方案**:
  - 后端集成 FastAPI WebSocket 或 SSE 端点
  - TaskManager 在步骤完成/消息更新时推送事件
  - 前端替换轮询为事件监听
- **收益**: 实时反馈、降低服务器负载、更好的用户体验

#### 3. 测试覆盖率提升

- **现状**: 仅 10 个测试覆盖 core 基础功能
- **方案**:
  - 优先补充：`task_manager.py`（编排核心）、`agent.py`（ReAct 循环）、API 路由
  - 使用 `pytest-asyncio` 测试异步逻辑
  - Mock OpenAI API 响应
  - 目标覆盖率 ≥ 60%
- **收益**: 保障重构安全、防止回归

---

### 📈 中优先级

#### 4. 配置系统重构

- **现状**: `AppSettings` 未使用，`default.yaml` 与代码脱节，路径硬编码
- **方案**:
  - 统一使用 pydantic-settings 管理所有配置
  - 支持 `.env`、环境变量、YAML 多来源
  - 移除硬编码路径（timeout、game_dir 等），全部可配置化
- **收益**: 配置一致性、部署灵活性

#### 5. 数据库持久化

- **现状**: 全部使用内存 + JSON 文件，任务历史查询效率低
- **方案**:
  - 引入 SQLite（轻量，无需额外服务）或 PostgreSQL
  - 使用 SQLAlchemy 或 Tortoise ORM
  - 迁移现有 JSON 数据
- **收益**: 查询性能、数据完整性、支持复杂统计

#### 6. 代码去重与重构

- 前端工具函数提取到 `utils/` 和 `composables/`
- `AssetQueryTool` 和 `ReadModelTool` 的 `resolve_game_dir()` 统一到 `_paths.py`
- 共享 CSS 提取到全局样式
- **收益**: 可维护性、一致性

#### 7. 国际化（i18n）

- **现状**: 前端 UI 文案全部硬编码中文
- **方案**: 使用 `vue-i18n` 支持多语言
- **收益**: 扩大用户群

#### 8. 前端错误边界与用户体验

- 添加 Vue ErrorBoundary 组件
- API 错误统一 Toast 通知
- Loading 骨架屏
- 操作撤销/重做
- **收益**: 更健壮的用户体验

---

### 🔮 远期规划

#### 9. 多工作流支持

- **现状**: 仅 Pipeline（顺序）一种工作流
- **方案**:
  - 支持分支/条件工作流
  - 人工审核节点（Human-in-the-loop）
  - 工作流可视化编辑器
- **收益**: 灵活编排、质量控制

#### 10. 插件/工具市场

- 支持自定义 Tool 注册
- 工具发现与组合
- 社区贡献工具包
- **收益**: 可扩展性

#### 11. 多模型对比与 A/B 测试

- 同一任务使用不同模型执行
- 结果对比与评分
- 最优模型推荐
- **收益**: 输出质量优化

#### 12. Docker 化部署

- 提供 Dockerfile 和 docker-compose.yml
- 一键部署，环境一致
- 支持 GPU 加速配置
- **收益**: 部署便利性

#### 13. 生成历史版本管理

- 任务步骤结果支持版本对比
- Diff 视图
- 回滚到历史版本
- **收益**: 迭代控制、质量追溯

#### 14. 性能监控与告警

- Token 消耗趋势图
- LLM 响应延迟监控
- 异常调用告警
- **收益**: 运营可视化和成本控制

#### 15. 知识库增强

- 支持向量数据库（如 ChromaDB）语义检索
- 自动从游戏资源提取知识
- 知识条目版本管理
- **收益**: 知识检索精度

#### 16. 素材管理增强

- 素材预览缩略图
- 标签与分类系统
- 素材使用频率统计
- **进度**: `ReadModelTool` 已实现从 model.json 提取 motions/expressions；`AssetQueryTool` 已优化为仅返回模型文件
- **收益**: 素材利用效率

---

## 五、问题优先级矩阵

| 优先级 | 问题 | 影响范围 | 修复难度 |
|--------|------|----------|----------|
| P1 | ReadFileTool 路径过宽 | 安全 | 低 |
| P1 | API 调用超时硬编码 | 稳定性 | 低 |
| P1 | LLM 调用无重试 | 稳定性 | 低 |
| P2 | 类型安全 | 代码质量 | 中 |
| P2 | 统一异常处理 | 稳定性 | 低 |
| P2 | 测试覆盖率 | 质量 | 高 |
| P3 | 路径解析逻辑重复 | 可维护性 | 低 |
| P3 | 未使用代码清理 | 整洁度 | 低 |
| P3 | CSS 重复 | 可维护性 | 低 |
| P3 | 配置系统统一 | 架构 | 中 |

---

*最后更新: 2026-05-12*
