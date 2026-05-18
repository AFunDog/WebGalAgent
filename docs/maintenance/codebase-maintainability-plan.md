# WebGalAgent 代码结构与可维护性优化方案

最后更新: 2026-05-18

本文档只保留当前仍有价值的“不改功能”整理方向。已经完成或明显过时的建议已移除。

## 已完成整理

截至 2026-05-18，本轮已完成以下拆分整理：

- `TaskManager` 已拆出：
  - `task_state.py`
  - `task_storage.py`
  - `task_context.py`
  - `task_agents.py`
- `browser/demo.py` 已拆出：
  - `demo_cli.py`
  - `demo_session.py`
- `browser/screencast.py` 已拆出：
  - `audio_capture.py`
  - `ffmpeg_encoder.py`
- 前端 API 已拆为分模块文件
- 前端已补：
  - `constants/pipeline.ts`
  - `utils/taskDisplay.ts`
  - `composables/useTaskPolling.ts`

当前仍值得继续整理的点：

- `PipelineView.vue` / `TasksView.vue` / `RecordView.vue` 的模板层仍偏大，后续如继续复杂化，建议再拆展示组件。

## 当前仍存在的问题

## 当前仍建议推进的事项

### P0

截至 2026-05-18，本轮 P0 已完成：

- 已为 `screencast.py`、`task_manager.py`、`PipelineView.vue`、`TasksView.vue`、`RecordView.vue` 补结构性注释。
- 已补最小保护测试：
  - `tests/api/test_task_manager_unit.py`
  - `tests/browser/test_demo_cli_unit.py`
  - `tests/frontend/test_view_contracts.py`
- 已补“权威来源”说明，减少后续继续重复维护相同配置的概率。

当前建议保留为维护约束，而不是继续作为待办：

- 大文件继续变复杂时，优先先补结构注释和契约测试，再拆组件或模块。
- 新增录制参数或流程步骤时，同步更新下文列出的权威来源文件。

## 当前权威来源

### 流水线步骤元数据

- 后端执行顺序与依赖定义：`src/webgal_agent/api/workflow_definition.py`
- 前端展示标签与依赖镜像：`src/frontend/src/constants/pipeline.ts`
- 任务输入拼接规则：`src/webgal_agent/api/task_context.py`

这里仍然存在“前后端各保留一份展示定义”的现实，但当前已经集中到了单文件级别，不再散落在多个页面和路由里。

### 录制配置来源

- 默认值文件：`src/configs/record.yaml`
- API 请求/响应模型：`src/webgal_agent/api/routes/record.py`
- CLI 参数入口：`src/webgal_agent/browser/demo_cli.py`
- 浏览器录制会话参数落点：`src/webgal_agent/browser/demo_session.py`
- 前端表单类型与提交结构：`src/frontend/src/types/index.ts`、`src/frontend/src/views/RecordView.vue`

后续如果新增录制参数，至少要同时检查这五处，而不是只改其中一层。

### P1

- 继续拆分 `PipelineView.vue` / `TasksView.vue` / `RecordView.vue` 的展示层。
- 把 WebGal 注入与配置写回进一步模块化，减少 `demo_session.py` 的会话负担。
- 统一前后端错误结构和日志字段。

### P2

- 统一工作流定义源，减少前后端重复维护。
- 统一录制配置默认值、接口模型与 CLI 参数来源。

## 当前保留这些文档的原因

- `docs/architecture/architecture-overview.md`: 描述当前真实分层。
- `docs/architecture/task-pipeline.md`: 描述任务编排与持久化结构。
- `docs/architecture/recording-flow.md`: 描述录制链路和子进程协议。

## 结论

当前最值得继续做的不是再大规模拆后端，而是：

- 继续压缩前端大页面
- 补关键路径测试
- 统一少数仍重复维护的配置和约束
