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

- Fixed-FPS element recording lives in `src/webgal_agent/browser/client.py`, `capture.py`, and `recorder.py`.
- For WebGal pages, the actual rendered target is usually `div#root`, not a raw `canvas`.
- In CLI/demo flows, prefer an auto-detect selector strategy: try `#root` first for WebGal, then fall back to `canvas` for generic animation demos.
- Do not treat `performance.now()` / `Date.now()` patching alone as enough for deterministic capture. That only changes time reads, but does not freeze render scheduling.
- There are two levels of setup:
  `enable_time_control()` patches the current page.
  `prepare_time_control()` is the deterministic path and must run before navigation so page scripts never see the native RAF scheduler.
- The stable approach used here is:
  1. Before navigation, install the RAF hook into the browser context with `add_init_script(...)`.
  2. Hook `requestAnimationFrame` and `cancelAnimationFrame` in page context.
  3. Queue RAF callbacks instead of letting the browser clock drive them.
  4. Expose `window.__advanceFrame()` that increments virtual time by `1000 / fps`, drains queued RAF callbacks, and awaits a microtask tick.
  5. In Python, record in time-control mode by advancing exactly one virtual frame per captured frame.
- Calling `enable_time_control()` only after the page has already loaded is not fully deterministic, because early page code may already have scheduled native RAF callbacks before the hook is installed.
- Determinism should be verified, not just “script injected successfully”.
  Use `verify_time_control()` to schedule a known RAF loop, advance a fixed number of frames, and confirm the observed timestamps match the expected sequence.
- In time-control mode, capture termination must be based on target frame count, not wall-clock time.
  Example: `duration=3`, `fps=30` means exactly `90` frames should be captured.
- `RecordingResult.duration` should report the virtual/video duration in time-control mode, not the real encode time.
- For extraction, prefer direct bitmap export only when the selected element is actually a `canvas`:
  `canvas.toDataURL("image/png")`
  and decode it in Python.
- For normal DOM targets such as `#root`, use Playwright element screenshot on the selected locator.
- Avoid full-page screenshot plus crop for fixed-FPS capture unless there is no alternative; it is much slower and causes unstable sampling.
- Verified command for this repo:
  `python -m webgal_agent.browser.demo record --url https://cl.yuzhes.com/demos/001-particles --output data/temp/video_fixed.avi --duration 3 --fps 30`
  Expected result after the fix: `90` frames, `30.0 FPS`, `3.0s`, and `逐帧验证: True`.
