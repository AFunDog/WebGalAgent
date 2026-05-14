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
- **`src/webgal_agent/api/`** — FastAPI REST API (tasks, knowledge, workflow, providers, assets); frontend served from `api/static/`
- **`src/webgal_agent/tools/`** — Agent tools: file read/write, asset query, Live2D model.json reader
- **`src/webgal_agent/config/`** — YAML-based config management (`default.yaml`, `providers.yaml`, `prompts.yaml`)

## Configuration

- `src/configs/default.yaml` — App defaults, game asset paths (hardcoded), LLM settings, agent model overrides
- `src/configs/providers.yaml` — LLM provider configs (API keys, base URLs, model names); not checked in
- `src/configs/prompts.yaml` — System prompts per agent + knowledge category/tag filters

## Code Conventions

- Python: ruff formatting, 100 char line limit, type hints throughout
- TypeScript: strict mode, no unused locals/parameters, ESNext modules, bundler module resolution
- Vue: Composition API with `<script setup lang="ts">`, vue-router hash history
- Pydantic v2 models for all data structures
- Agent tools extend `Tool` ABC with JSON Schema `parameters`

## Browser Recording Notes

- Fixed-FPS browser recording now uses `CCapture.js` in `src/webgal_agent/browser/capture.py` and `recorder.py`.
- Vendored browser assets live in `src/webgal_agent/browser/assets/`:
  `CCapture.all.min.js` and `html2canvas.min.js`.
- For WebGal pages, the real target is usually `div#root`, not a raw `canvas`.
- In CLI/demo flows, prefer an auto-detect selector strategy: try `#root` first for WebGal, then fall back to `canvas` for generic animation demos.
- `CCapture.js` is responsible for fixed-framerate time stepping and frame capture.
- Because WebGal often renders the final scene as DOM under `#root`, the capture bridge rasterizes non-canvas targets with `html2canvas(...)` into a hidden mirror canvas, then hands that canvas to `CCapture`.
- For native canvas targets, the bridge passes the source canvas directly to `CCapture` without the extra rasterization step.
- The current backend writes browser-generated `webm` output. `VideoConfig.codec` should be `webm`.
- Verified command for this repo:
  `python -m webgal_agent.browser.demo record --url https://cl.yuzhes.com/demos/001-particles --output data/temp/output.webm --duration 3 --fps 30`
