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

WebGalAgent is a multi-agent workflow for visual novel writing and WebGal script generation.

Main stages:

`outline_writer -> script_writer -> script_converter`

The repository also includes a browser automation and recording subsystem used to preview and record WebGal games.

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
- `src/webgal_agent/api/`: FastAPI app, task manager, routes
- `src/webgal_agent/browser/`: browser client, demo CLI, screencast recorder
- `src/webgal_agent/tools/`: agent tools
- `src/configs/`: `default.yaml`, `prompts.yaml`, `providers.yaml.sample`, `record.yaml`
- `src/frontend/`: frontend app
- `data/knowledge/`: markdown knowledge base
- `docs/roadmap/issues-and-roadmap.md`: active engineering issues and roadmap

## Current Browser Recording Model

- Preferred recorder is `ScreencastRecorder` in `src/webgal_agent/browser/screencast.py`
- It uses `Page.startScreencast` to pull JPEG/PNG frames from Chromium compositor
- Frames are written to a temporary directory under `data/browser/temp/`
- After capture, FFmpeg encodes frames offline into `.mp4` or `.webm`
- Optional audio capture uses WebAudio hook + `MediaStreamTrackProcessor` and is merged later as WAV input
- API recording route `src/webgal_agent/api/routes/record.py` runs the CLI as a subprocess instead of embedding Playwright inside FastAPI

## Browser Recording Rules

- Keep recording-related behavior aligned across:
  - `src/webgal_agent/browser/demo.py`
  - `src/webgal_agent/browser/screencast.py`
  - `src/webgal_agent/api/routes/record.py`
- `--selector auto` should try `#root` first, then `canvas`
- `--duration 0` is valid only when `--stop-on` is provided
- Use `msedge` channel only when the repo already expects Edge behavior; do not silently switch browsers in docs or code

## WebGal Config Injection Rule

When injecting game config through IndexedDB in `browser/demo.py`:

- `window.saveConfig()` must be treated as an async IndexedDB write trigger even if it is called like a normal function
- Do not touch the same IndexedDB store immediately after `saveConfig()`
- Leave a short delay first; current debugging established that immediate access can conflict with the write started by `saveConfig()`
- The IndexedDB database name is `localforage`, not `_localforage`

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
