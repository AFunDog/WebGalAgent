# WebGalAgent

Working notes for Codex and other code agents in this repository.

## Interpreter Rule

- Use the project virtualenv Python by default: `.venv\Scripts\python.exe`
- Do not assume `python` on PATH is the correct interpreter
- Prefer commands like:

```powershell
.\.venv\Scripts\python.exe start.py --dev
.\.venv\Scripts\python.exe -m webgal_agent
.\.venv\Scripts\python.exe -m webgal_agent.browser.demo record --url http://localhost:3001
```

## Project Summary

WebGalAgent is a local workbench for visual-novel writing and WebGal script generation.

Main stages:

`outline_writer -> script_writer -> script_converter`

The repository also includes browser automation and recording support for previewing and capturing WebGal games.

## Tech Stack

- Backend: Python 3.12+, FastAPI, Pydantic v2, httpx, OpenAI SDK
- Frontend: Vue 3, Vue Router 4, Vite 6, TypeScript
- Packaging: hatchling
- Tests: pytest, pytest-asyncio
- Lint: ruff
- Browser: Playwright + CDP + FFmpeg

## Important Paths

- `src/webgal_agent/core/`: agent base classes, memory, message model
- `src/webgal_agent/agents/`: concrete agent wrappers
- `src/webgal_agent/api/`: FastAPI app, task manager, routes, workflow metadata
- `src/webgal_agent/browser/`: browser client, demo CLI, screencast recorder
- `src/webgal_agent/knowledge/`: knowledge loading plus multimodal character-asset description generation
- `src/webgal_agent/scene_link/`: scene-link manager for mapping results into the WebGal game tree
- `src/webgal_agent/tools/`: agent tools
- `src/configs/`: `default.yaml`, `prompts.yaml`, `providers.yaml`, `providers.yaml.sample`, `record.yaml`
- `src/frontend/`: frontend app
- `data/knowledge/`: Markdown knowledge base plus generated character expression/action JSON
- `docs/roadmap/issues-and-roadmap.md`: active engineering issues and roadmap

## Knowledge Model

- Character identity/background lives in `profile.md`
- Character expression/motion guidance lives in `expression_motion.md`
- Generated action/expression mappings live in `expression_motion.json`
- The knowledge store loads Markdown files and also loads `characters/**/expression_motion.json`
- For `script_converter`, prefer the JSON data when both JSON and Markdown exist; use the Markdown explanation only as a fallback
- `search_expression_motion` still exists as a standalone test/retrieval helper, but it is not part of the normal `script_converter` tool surface
- `query_assets` now has a local CLI entry: `.\.venv\Scripts\python.exe -m webgal_agent.tools.asset_query_cli --asset-type character`

## Current Browser Recording Model

- Preferred recorder is `ScreencastRecorder` in `src/webgal_agent/browser/screencast.py`
- It uses `Page.startScreencast` to pull JPEG/PNG frames from Chromium compositor
- Frames are written to a temporary directory under `data/browser/temp/`
- After capture, FFmpeg encodes frames offline into `.mp4` or `.webm`
- Optional audio capture uses WebAudio hook + `MediaStreamTrackProcessor` and is merged later as WAV input
- API recording route `src/webgal_agent/api/routes/record.py` runs the CLI as a subprocess instead of embedding Playwright inside FastAPI
- `--selector auto` should try `#root` first, then `canvas`
- `--duration 0` is valid only when `--stop-on` is provided
- `window.saveConfig()` is an async IndexedDB write trigger; do not touch the same store immediately after calling it
- Feedback-based step revision should feed the previous step output back into the model and preserve both the old and new outputs in task history for comparison

## Windows Event Loop Rule

On Windows, Playwright requires `WindowsProactorEventLoopPolicy`.

Set it only in entry points before importing Playwright or uvicorn:

- `src/webgal_agent/__main__.py`
- `src/webgal_agent/browser/demo.py`

Do not set it in business modules such as:

- `src/webgal_agent/api/app.py`
- `src/webgal_agent/browser/client.py`
- `src/webgal_agent/browser/screencast.py`

## Working Style

- Read the relevant code before editing
- Prefer `rg` / `rg --files` for search
- Keep edits local and minimal
- Do not revert unrelated user changes
- When changing response shapes in backend routes, check the frontend API and views
- When touching recording code, validate assumptions against the actual code, not old docs
- When updating docs, treat code as the source of truth and rewrite stale prose instead of patching around it

## Validation

Prefer the smallest useful check:

- Syntax check:

```powershell
.\.venv\Scripts\python.exe -c "import ast, pathlib; ast.parse(pathlib.Path('src/webgal_agent/browser/demo.py').read_text(encoding='utf-8'))"
```

- Tests:

```powershell
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest
```

- Lint:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
```

- Frontend build:

```powershell
npm run build --prefix src/frontend
```

## Documentation Maintenance

If behavior changes, keep these docs in sync:

- `README.md`
- `src/webgal_agent/browser/README.md`
- `docs/roadmap/issues-and-roadmap.md`
- `AGENTS.md`
