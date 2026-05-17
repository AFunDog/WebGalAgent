# WebGalAgent

多智能体视觉小说创作与 WebGal 录制工具集。

## 概览

WebGalAgent 把视觉小说内容生产拆成三步：

`outline_writer -> script_writer -> script_converter`

前两步负责从想法生成大纲和剧本，最后一步把剧本转换成 WebGal 引擎可执行脚本。项目还包含一个浏览器录制子系统，用于录制 WebGal 游戏运行画面。

## 主要能力

- 多智能体顺序流水线生成剧本
- 基于 Markdown + Frontmatter 的知识库检索
- FastAPI 后端 + Vue 3 前端
- Playwright/CDP 浏览器自动化
- WebGal 游戏高帧率录制
- Web UI 驱动的录制子进程模式

## 环境要求

- Python 3.12+
- Node.js + npm
- FFmpeg
- Playwright 浏览器依赖

## 解释器约定

本项目默认使用虚拟环境解释器：

```powershell
.\.venv\Scripts\python.exe
```

不要默认使用系统 `python`。

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\activate
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m playwright install chromium
```

确认 FFmpeg 在 PATH 中：

```powershell
ffmpeg -version
```

## 配置

项目使用 `src/configs/` 下的 YAML 文件：

- `default.yaml`: 应用默认配置
- `prompts.yaml`: 智能体提示词与知识需求
- `providers.yaml.sample`: LLM 提供商配置样例
- `record.yaml`: 浏览器录制默认参数

实际使用时复制并填写 `src/configs/providers.yaml`。

最小示例：

```yaml
defaults: &defaults
  provider: openai
  model: gpt-4o
  base_url: https://api.openai.com/v1
  api_key: "sk-..."
  temperature: 0.7
  max_tokens: 4096

outline_writer:
  <<: *defaults

script_writer:
  <<: *defaults

script_converter:
  <<: *defaults
```

## 启动

开发模式：

```powershell
.\.venv\Scripts\python.exe start.py --dev
```

生产式本地启动：

```powershell
.\.venv\Scripts\python.exe start.py
```

只启动后端：

```powershell
.\.venv\Scripts\python.exe -m webgal_agent
```

前端单独开发：

```powershell
npm run dev --prefix src/frontend
```

## 浏览器录制

录制模块位于 `src/webgal_agent/browser/`，推荐方案是 `ScreencastRecorder`：

- 通过 CDP `Page.startScreencast` 抓取 compositor 帧
- 原始帧先写入 `data/temp/` 临时目录
- 录制结束后调用 FFmpeg 离线编码
- 支持可选 WebAudio 捕获并与视频合流

典型命令：

```powershell
.\.venv\Scripts\python.exe -m webgal_agent.browser.demo record `
  --url http://localhost:3001/games/MyGO3.0.0/ `
  --output data/temp/output.mp4 `
  --fps 60 --width 1920 --height 1080 `
  --format jpeg
```

常用参数：

| 参数 | 说明 |
|------|------|
| `--url` | 目标页面 |
| `--output` | 输出文件 |
| `--duration` | 最大录制时长；为 `0` 时必须配合 `--stop-on` |
| `--stop-on` | 轮询求值的 JS 停止条件 |
| `--selector` | `auto` / 指定 CSS 选择器 |
| `--record-audio` | 捕获页面音频 |
| `--game-config` | 通过 IndexedDB 注入 WebGal 配置 |

### WebGal 配置注入注意事项

当前已知结论：

- IndexedDB 数据库名是 `localforage`
- `window.saveConfig()` 会触发异步数据库写入
- 在 `saveConfig()` 后立刻操作同一个 store，可能与其内部异步写入冲突
- 因此注入逻辑需要在 `saveConfig()` 后留一个短延迟

浏览器模块的更多细节见 [src/webgal_agent/browser/README.md](d:/GitRepository/WebGalAgent/src/webgal_agent/browser/README.md)。

## 知识库

知识库目录在 `data/knowledge/`，使用 Markdown + YAML Frontmatter：

```markdown
---
category: character
tags: [webgal, compact]
title: 千早爱音
---

# 千早爱音
...
```

常见分类：

- `character`
- `setting`
- `plot`
- `reference`
- `custom`

每个智能体可在 `src/configs/prompts.yaml` 中声明需要的 `categories` 与 `tags`。

## API

主要 API 路由：

- `/api/tasks`
- `/api/knowledge`
- `/api/workflows`
- `/api/providers`
- `/api/scene-link`
- `/api/record`

录制接口：

- `POST /api/record/start`
- `POST /api/record/stop`
- `GET /api/record/status`
- `GET /api/record/config`

## 目录结构

```text
WebGalAgent/
├── start.py
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

## 开发检查

```powershell
.\.venv\Scripts\python.exe -m ruff check .
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest
npm run build --prefix src/frontend
```

## 已知文档入口

- 工程协作说明: [AGENTS.md](d:/GitRepository/WebGalAgent/AGENTS.md)
- 浏览器模块文档: [src/webgal_agent/browser/README.md](d:/GitRepository/WebGalAgent/src/webgal_agent/browser/README.md)
- 问题与路线图: [docs/issues-and-roadmap.md](d:/GitRepository/WebGalAgent/docs/issues-and-roadmap.md)
