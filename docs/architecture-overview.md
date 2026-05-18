# WebGalAgent 架构概览

最后更新: 2026-05-18

本文档描述当前代码的真实分层与主要数据流，作为后续重构和协作的公共参考。

## 顶层分层

- `src/webgal_agent/core/`
  负责消息模型、智能体基类、记忆抽象。
- `src/webgal_agent/agents/`
  负责三个具体智能体封装：`outline_writer`、`script_writer`、`script_converter`。
- `src/webgal_agent/api/`
  负责 FastAPI 应用、任务管理、只读/写路由。
- `src/webgal_agent/browser/`
  负责浏览器自动化、页面注入、录制 CLI、Screencast 录制器。
- `src/webgal_agent/knowledge/`
  负责 Markdown + Frontmatter 知识库加载与查询。
- `src/frontend/`
  负责 Vue 3 Web UI。

## 本轮拆分结果

### API 流水线层

原先集中在 `task_manager.py` 的逻辑已拆分为：

- `task_manager.py`: 编排入口与状态协调
- `task_state.py`: `TaskInfo` 与工作流响应结构
- `task_storage.py`: 任务落盘与恢复
- `task_context.py`: 知识上下文和步骤输入构建
- `task_agents.py`: agent 构建与 agent 信息映射

### Browser 录制层

原先集中在 `demo.py` 与 `screencast.py` 的部分逻辑已拆分为：

- `demo.py`: CLI 入口
- `demo_cli.py`: 参数解析与模式分发
- `demo_session.py`: 导航与录制会话实现
- `webgal_injection.py`: 页面注入常量
- `audio_capture.py`: 音频抓取与 WAV 落盘
- `ffmpeg_encoder.py`: FFmpeg 编码辅助

### 前端组织层

前端已补充以下共享层：

- `src/frontend/src/api/*.ts`: 分模块 API
- `src/frontend/src/composables/useTaskPolling.ts`: 共享轮询逻辑
- `src/frontend/src/constants/pipeline.ts`: 流水线步骤定义
- `src/frontend/src/utils/taskDisplay.ts`: 状态/步骤/token 展示辅助

## 主要运行链路

### 任务流水线

1. 前端调用 `/api/tasks` 创建任务。
2. `TaskManager` 初始化任务状态并落盘到 `data/tasks/<task_id>/`。
3. 前端调用 `/api/tasks/{id}/run-step` 逐步推进。
4. `TaskManager` 为当前步骤构建 agent、知识上下文和前序输出上下文。
5. agent 调用 LLM，必要时触发工具调用。
6. 步骤输出写回内存任务状态，并同步持久化。

### 浏览器录制

1. 前端调用 `/api/record/start`。
2. 后端 `record.py` 子进程启动 `python -m webgal_agent.browser.demo record --json`。
3. `demo.py` 完成脚本注入、场景切换、可选配置注入、自动播放与录制准备。
4. `ScreencastRecorder` 通过 CDP `Page.startScreencast` 抓帧到磁盘。
5. 可选音频通过 WebAudio hook 抓取 PCM/WAV。
6. 录制结束后用 FFmpeg 离线编码，再把 JSON 结果回传给 API 层。

## 当前边界约束

- Playwright 不直接嵌入 FastAPI 业务进程。
- Windows event loop policy 只在入口点设置。
- `saveConfig()` 后必须留短延迟，再访问同一 IndexedDB store。
- `selector=auto` 固定尝试 `#root`、`canvas`。

## 当前维护重点

- `TaskManager` 仍是统一入口，但内部职责已拆开，后续应继续保持“对外稳定、内部分层”。
- browser 录制链路已从“单大文件”转为“CLI / 会话 / 注入 / 音频 / 编码”分层。
- `RecordView.vue`、`PipelineView.vue`、`TasksView.vue` 模板仍偏重，后续若继续加功能，建议再拆组件层。
