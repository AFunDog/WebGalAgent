# WebGalAgent

面向视觉小说创作与 WebGal 落地的本地工作台，当前代码基于三阶段文本流水线，加上知识库管理、场景软链接管理和浏览器录制子系统。

## 当前项目范围

- 三阶段流水线：`outline_writer -> script_writer -> script_converter`
- FastAPI 后端 + Vue 3 前端工作台
- Markdown + Frontmatter 知识库
- LLM provider 配置管理
- WebGal 场景软链接切换
- 基于 Playwright + CDP + FFmpeg 的页面录制

这不是一个“只有录制器”或“只有多智能体框架”的仓库，当前真实形态是一个围绕 WebGal 工作流组织的本地工具集。

## 代码结构

```text
WebGalAgent/
├── start.py
├── AGENTS.md
├── docs/
├── data/
├── src/
│   ├── configs/
│   ├── frontend/
│   └── webgal_agent/
│       ├── agents/
│       ├── api/
│       ├── browser/
│       ├── config/
│       ├── core/
│       ├── knowledge/
│       ├── scene_link/
│       └── tools/
└── tests/
```

关键目录：

- `src/webgal_agent/api/`: FastAPI 应用、任务编排、录制/知识库/供应商/软链接路由
- `src/webgal_agent/browser/`: CLI、会话逻辑、录制器、音频抓取、FFmpeg 编码
- `src/webgal_agent/knowledge/`: 知识库加载、查询与角色动作素材知识生成
- `src/webgal_agent/scene_link/`: 场景软链接管理
- `src/frontend/`: 前端页面与 API 客户端
- `src/configs/`: 默认配置、提示词、provider 样例、录制默认值

## 环境要求

- Python 3.12+
- Node.js + npm
- FFmpeg
- Playwright 依赖浏览器

## 解释器约定

默认使用项目虚拟环境：

```powershell
.\.venv\Scripts\python.exe
```

不要假设系统 `python` 可直接使用。

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\activate
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m playwright install chromium
npm install --prefix src/frontend
```

确认 FFmpeg 可用：

```powershell
ffmpeg -version
```

## 配置

运行时主要依赖四类配置文件：

- `src/configs/default.yaml`: 应用级默认配置
- `src/configs/prompts.yaml`: 三个智能体的 system prompt 与知识需求
- `src/configs/providers.yaml`: 各智能体 LLM 配置，首次可从 `providers.yaml.sample` 复制
- `src/configs/record.yaml`: 录制页与录制 API 默认值

其中 provider 配置由后端和前端共用；录制默认值由 `/api/record/config` 读取后回填到 `RecordView.vue`。

## 启动方式

开发模式，同时启动后端和前端：

```powershell
.\.venv\Scripts\python.exe start.py --dev
```

生产式本地启动：

```powershell
.\.venv\Scripts\python.exe start.py
```

仅启动后端：

```powershell
.\.venv\Scripts\python.exe -m webgal_agent
```

仅启动前端开发服务器：

```powershell
npm run dev --prefix src/frontend
```

默认地址：

- 后端：`http://127.0.0.1:8000`
- 前端开发：`http://localhost:5173`

## 前端页面

当前路由入口：

- `/knowledge`: 知识库浏览与管理
- `/pipeline`: 流水线说明
- `/tasks`: 任务创建、单步执行、结果编辑
- `/providers`: LLM provider 配置
- `/scene-link`: WebGal 场景软链接切换与重置
- `/record`: 浏览器录制控制台

## 浏览器录制

当前录制模式是：

`前端 /record 页面 -> /api/record/* -> 子进程执行 browser.demo record -> ScreencastRecorder -> FFmpeg 离线编码`

重点事实：

- API 通过子进程调用 CLI，不把 Playwright 嵌进 FastAPI 进程
- 当前录制器是 `src/webgal_agent/browser/screencast.py` 中的 `ScreencastRecorder`
- 默认配置来自 `src/configs/record.yaml`
- CLI 默认 `--selector` 是 `auto`，会优先尝试 `#root`，再回退到 `canvas`
- 但前端默认值会先读取 `record.yaml`，所以页面默认录制目标以配置文件为准
- `window.saveConfig()` 会触发异步 IndexedDB 写入；配置注入时必须先短暂等待

详细录制说明见 [src/webgal_agent/browser/README.md](/d:/GitRepository/WebGalAgent/src/webgal_agent/browser/README.md)。

## 知识库约定

知识文件位于 `data/knowledge/`，每个 Markdown 文件对应一条知识条目，支持 YAML Frontmatter。

```markdown
---
category: character
tags: [mygo, profile]
title: 千早爱音
---

# 千早爱音
...
```

当前角色知识推荐保持两层：

- `profile.md`: 角色身份、背景、性格、关系
- `expression_motion.md`: 立绘、表情、动作、演出相关信息

仓库还提供一个多模态素材描述模块，可扫描角色目录下的图片/视频动作素材并生成 `expression_motion.json`：

```powershell
.\.venv\Scripts\python.exe -m webgal_agent.knowledge.asset_describer --asset-root data/figure_assets --character-id anon
```

说明：

- 模块默认读取 `providers.yaml` 中的 `asset_describer` 槽位
- 素材目录结构默认是 `data/figure_assets/<角色ID>/...`
- 文件名可直接使用状态名，如 `smile01.png`，也可使用 `anon__smile01.png`
- 输出文件为 `data/knowledge/characters/<角色名>/expression_motion.json`
- 图片会作为 `input_image` 发送；视频会作为通用文件输入发送，是否真正支持取决于所用模型和服务端

## 验证命令

```powershell
.\.venv\Scripts\python.exe -m ruff check .
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest
npm run build --prefix src/frontend
```

## 文档入口

- 协作约束与仓库约定：[AGENTS.md](/d:/GitRepository/WebGalAgent/AGENTS.md)
- 文档索引：[docs/README.md](/d:/GitRepository/WebGalAgent/docs/README.md)
- 浏览器录制专题：[src/webgal_agent/browser/README.md](/d:/GitRepository/WebGalAgent/src/webgal_agent/browser/README.md)
- 当前问题清单：[docs/roadmap/issues-and-roadmap.md](/d:/GitRepository/WebGalAgent/docs/roadmap/issues-and-roadmap.md)
