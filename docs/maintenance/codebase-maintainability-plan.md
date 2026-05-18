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

- 为 `screencast.py`、`task_manager.py`、前端大页面补结构性注释。
- 补 `TaskManager`、录制 CLI、前端关键交互的最小保护测试。
- 收敛仍然分散的录制配置来源与步骤元数据说明。

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
