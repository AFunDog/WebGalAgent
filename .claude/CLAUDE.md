# WebGalAgent

Multi-agent collaborative workflow for creating visual novel scripts, powered by LLMs. Three agents (OutlineWriter → ScriptWriter → ScriptConverter) transform user ideas into WebGal engine executable scripts.

## Tech Stack

- **Backend**: Python 3.12+, FastAPI, Pydantic v2, httpx, openai SDK
- **Frontend**: Vue 3 (Composition API, `<script setup lang="ts">`), Vue Router 4, Vite 6, TypeScript 5.7 (strict mode)
- **Package/Build**: hatchling (Python), pnpm/npm (frontend)
- **Test**: pytest + pytest-asyncio (asyncio_mode=auto)
- **Lint**: ruff (line-length 100, rules E/F/I/N/UP/B/SIM)

## Key Commands

```bash
# One-click start (build frontend + start backend)
python start.py

# Development with hot-reload
python start.py --dev

# Backend only
python -m webgal_agent

# Frontend dev (port 5173, proxies API to :8000)
cd src/frontend && npm run dev

# Browser recording CLI
python -m webgal_agent.browser.demo record --url <url> --duration 10 --fps 60

# Run tests
pytest

# Lint
ruff check .
```

## Architecture

```
User Input → OutlineWriter → ScriptWriter → ScriptConverter → WebGal .txt files
                ↑                ↑               ↑
            Knowledge Base (Markdown files with YAML frontmatter)
```

- **`src/webgal_agent/core/`** — Agent base class (state machine, LLM calling, ReAct tool-use loop), Message, Workflow, Memory
- **`src/webgal_agent/agents/`** — Three thin agent subclasses; behavior defined by system prompts in `src/configs/prompts.yaml`
- **`src/webgal_agent/workflows/pipeline.py`** — Sequential pipeline with cumulative context accumulation
- **`src/webgal_agent/knowledge/`** — File-based knowledge store parsing `data/knowledge/**/*.md` with YAML frontmatter
- **`src/webgal_agent/api/`** — FastAPI REST API (tasks, knowledge, workflow, providers, assets, scene_link, record); frontend served from `api/static/`
- **`src/webgal_agent/tools/`** — Agent tools: file read/write, asset query, Live2D model.json reader
- **`src/webgal_agent/config/`** — YAML-based config management (`default.yaml`, `providers.yaml`, `prompts.yaml`)
- **`src/webgal_agent/browser/`** — Playwright browser automation + CDP Screencast video recording
- **`src/webgal_agent/scene_link/`** — Scene link manager for connecting task outputs to WebGal game directories

## Configuration

- `src/configs/default.yaml` — App defaults, game asset paths, LLM settings, agent model overrides
- `src/configs/providers.yaml` — LLM provider configs (API keys, base URLs, model names); not checked in
- `src/configs/prompts.yaml` — System prompts per agent + knowledge category/tag filters
- `src/configs/record.yaml` — Browser recording defaults (URL, fps, duration, selector, etc.)

## Code Conventions

- Python: ruff formatting, 100 char line limit, type hints throughout
- TypeScript: strict mode, no unused locals/parameters, ESNext modules, bundler module resolution
- Vue: Composition API with `<script setup lang="ts">`, vue-router hash history
- Pydantic v2 models for all data structures
- Agent tools extend `Tool` ABC with JSON Schema `parameters`

## Windows Event Loop

On Windows, Playwright requires `WindowsProactorEventLoopPolicy`. All entry points set this before importing playwright/uvicorn:

- **`src/webgal_agent/__main__.py`** — Set before `import uvicorn`; uvicorn.run uses `loop="asyncio"`
- **`src/webgal_agent/browser/demo.py`** — Set before `from webgal_agent.browser import ...`
- **`start.py`** — Uses `python -m webgal_agent` (routed through `__main__.py`) instead of `python -m uvicorn` directly

**Never** set event loop policy in business code (`app.py`, `client.py`, `screencast.py`).

## Browser Recording

- **Recording approach**: CDP Screencast (`Page.startScreencast`) — pulls JPEG/PNG frames directly from Chromium compositor, completely bypassing Playwright's MediaRecorder (25fps limit). Frames are piped to ffmpeg for encoding.
- **Key classes**:
  - `ScreencastRecorder` (`src/webgal_agent/browser/screencast.py`) — main recorder using CDP + ffmpeg
  - `BrowserClient` (`src/webgal_agent/browser/client.py`) — Playwright browser lifecycle, CDP session, script injection
- **API integration**: `record.py` spawns the CLI (`python -m webgal_agent.browser.demo record --json`) as a **subprocess** — Playwright runs in its own process, fully isolated from FastAPI/Uvicorn event loop.
- **Output**: mp4 (H.264 via libx264) or webm (VP9 via libvpx-vp9), auto-detected from file extension.
- **Supported formats**: jpeg (faster, smaller) and png (lossless, best quality).
- **Auto-detect selector**: `--selector auto` tries `#root` then `canvas`.
- **Legacy**: `CanvasCapture` (CCapture.js) and `VideoRecorder` (HeadlessExperimental.beginFrame) are retained for special use cases.
- **CLI verified command**:
  ```bash
  python -m webgal_agent.browser.demo record \
    --url http://localhost:3001/games/MyGO3.0.0/ \
    --output data/temp/output.mp4 --duration 10 --fps 60 \
    --width 1920 --height 1080
  ```
