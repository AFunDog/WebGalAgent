# WebGalAgent

Guidance for Codex and other code agents working in this repository.

## Purpose

WebGalAgent is a multi-agent workflow for creating visual novel scripts. It transforms a user idea into WebGal-compatible script files through three sequential agents:

`OutlineWriter -> ScriptWriter -> ScriptConverter`

The system combines:

- a FastAPI backend
- a Vue 3 + TypeScript frontend
- YAML-based configuration
- a file-based knowledge base
- Playwright/CDP-based browser recording tools

## Tech Stack

- Backend: Python 3.12+, FastAPI, Pydantic v2, httpx, openai SDK
- Frontend: Vue 3, Vue Router 4, Vite 6, TypeScript 5.x, `<script setup lang="ts">`
- Packaging: hatchling
- Tests: pytest, pytest-asyncio
- Lint: ruff

## Key Commands

```bash
# use the project virtualenv python by default
.venv\Scripts\python.exe start.py

# start full app
python start.py

# start with hot reload
python start.py --dev

# backend only
python -m webgal_agent

# frontend dev server
cd src/frontend && npm run dev

# tests
pytest

# lint
ruff check .

# browser recording CLI
python -m webgal_agent.browser.demo record --url <url> --duration 10 --fps 60
```

## Environment Rule

- Prefer the project virtualenv Python for all Python commands: `.venv\Scripts\python.exe`
- Do not assume `python` on PATH points at the correct interpreter

## Repository Map

- `src/webgal_agent/core/`: agent base class, message model, workflow primitives, memory
- `src/webgal_agent/agents/`: thin agent implementations
- `src/webgal_agent/workflows/`: sequential pipeline orchestration
- `src/webgal_agent/knowledge/`: knowledge store and models
- `src/webgal_agent/api/`: FastAPI app, task manager, route handlers
- `src/webgal_agent/tools/`: tool abstractions and file/asset helpers
- `src/webgal_agent/browser/`: Playwright/CDP browser automation and recording
- `src/webgal_agent/scene_link/`: scene linking utilities
- `src/configs/`: YAML configuration files
- `src/frontend/`: Vue frontend
- `data/knowledge/`: markdown knowledge base files with YAML frontmatter
- `tests/`: backend and browser tests

## Important Config Files

- `src/configs/default.yaml`: app defaults, asset paths, model settings
- `src/configs/providers.yaml.sample`: provider config template
- `src/configs/prompts.yaml`: system prompts and knowledge filters
- `src/configs/record.yaml`: browser recording defaults

## Architecture Notes

- Agent behavior is mostly defined by prompt/configuration, not large subclasses.
- The pipeline is sequential and passes cumulative context through each stage.
- The knowledge base is file-backed and parsed from markdown with frontmatter.
- Recording support is intentionally isolated from the API process by invoking the browser demo CLI as a subprocess.

## Browser Recording Rules

- Preferred recording path is CDP Screencast via `Page.startScreencast`.
- Main implementation lives in `src/webgal_agent/browser/screencast.py`.
- API route `src/webgal_agent/api/routes/record.py` should call the demo CLI as a subprocess instead of embedding Playwright directly in the FastAPI event loop.
- Output format is inferred from file extension, typically `.mp4` or `.webm`.
- `--selector auto` should try `#root` then `canvas`.
- In WebGal config injection, `window.saveConfig()` is effectively an async IndexedDB write even if called like a normal function. Do not touch the same IndexedDB store immediately afterward; leave a short delay first to avoid write conflicts.

## Windows Event Loop Rule

Playwright on Windows requires `WindowsProactorEventLoopPolicy`.

Set that policy only in entry points before importing Playwright or uvicorn:

- `src/webgal_agent/__main__.py`
- `src/webgal_agent/browser/demo.py`
- `start.py`

Do not add event loop policy changes inside business code such as:

- `src/webgal_agent/api/app.py`
- `src/webgal_agent/browser/client.py`
- `src/webgal_agent/browser/screencast.py`

## Code Conventions

- Prefer small, localized changes that match existing structure.
- Use type hints throughout Python changes.
- Keep Python compatible with the repository's ruff rules and 100-character line length.
- Use Pydantic v2 patterns for data models.
- Keep Vue code in Composition API style with `<script setup lang="ts">`.
- Maintain TypeScript strict-mode compatibility.
- Agent tools should continue to follow the existing `Tool` abstraction and JSON-schema-style parameters.

## Working Rules For Agents

- Read the relevant code before editing; do not infer architecture from filenames alone.
- Prefer `rg` and `rg --files` for search.
- Validate changes with the narrowest useful checks first, then broader checks if needed.
- Do not rewrite unrelated files or reformat large areas without reason.
- Preserve user changes already present in the worktree.
- When touching recording code, verify interactions across `demo.py`, `screencast.py`, and `api/routes/record.py`.
- When touching prompts or config-driven behavior, inspect the corresponding YAML under `src/configs/`.
- When changing API behavior, check whether the frontend in `src/frontend/src/api/` or related views depend on the response shape.

## Validation Expectations

Use the smallest relevant command set:

- Python logic: `pytest` on targeted tests, then broader tests if needed
- Lint-sensitive edits: `ruff check .`
- Frontend edits: `npm run build` or targeted frontend checks when appropriate
- Recording changes: run the browser demo CLI or route-level tests if available

## Preferred Change Style

- Fix root causes, not only symptoms.
- Keep interfaces stable unless the task requires a contract change.
- If a contract changes, update all affected layers: backend, frontend, config, and tests.
- Add concise comments only where the code would otherwise be hard to follow.
