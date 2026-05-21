# WebGalAgent 架构概览

最后更新: 2026-05-21

本文档只保留顶层模块边界和两条主运行链路。更细的任务编排和录制细节分别放在独立文档中。

## 顶层结构

- `src/webgal_agent/core/`: 消息模型、Agent 基类、记忆抽象
- `src/webgal_agent/agents/`: `outline_writer`、`script_writer`、`script_converter`
- `src/webgal_agent/api/`: FastAPI 应用、任务编排、各类路由
- `src/webgal_agent/browser/`: 浏览器自动化、页面注入、录制 CLI、Screencast 录制
- `src/webgal_agent/knowledge/`: Markdown + Frontmatter 知识库
- `src/webgal_agent/scene_link/`: WebGal 场景软链接管理
- `src/frontend/`: Vue 3 前端工作台

## 两条主链路

### 1. 文本流水线

```text
前端 /tasks
  -> /api/tasks
  -> TaskManager
  -> outline_writer
  -> script_writer
  -> script_converter
  -> data/tasks/<task_id>/*
```

特点：

- 当前固定三步执行顺序
- 单步执行与结果编辑都由 `TaskManager` 协调
- 步骤输出会持久化到 `data/tasks/<task_id>/`

细节见 [task-pipeline.md](./task-pipeline.md)。

### 2. 浏览器录制

```text
前端 /record
  -> /api/record/*
  -> 子进程 demo.py
  -> demo_session.py
  -> ScreencastRecorder
  -> data/browser/temp/*
  -> ffmpeg 编码输出
```

特点：

- Playwright 与 FastAPI 进程隔离
- 当前默认录制器是 `ScreencastRecorder`
- 页面录制默认值来自 `src/configs/record.yaml`

细节见 [recording-flow.md](./recording-flow.md)。

## 前端职责

前端当前主要是工作台，不承担核心业务实现：

- `KnowledgeView.vue`: 知识库浏览与编辑
- `PipelineView.vue`: 流水线结构展示
- `TasksView.vue`: 任务管理与步骤推进
- `ProvidersView.vue`: LLM provider 配置
- `SceneLinkView.vue`: 场景软链接切换
- `RecordView.vue`: 浏览器录制控制台

## 关键边界

- Windows event loop policy 只在入口点设定
- 录制 API 只负责子进程协议，不直接运行 Playwright
- `saveConfig()` 后必须短暂等待，避免 IndexedDB 写冲突
- README 负责“怎么用”，roadmap 负责“待解决什么”，不要互相混写
