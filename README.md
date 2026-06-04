# WebGalAgent

WebGalAgent is a local workbench for visual-novel writing and WebGal script generation. The current codebase is centered on a three-stage pipeline, a file-backed knowledge base, a scene-link manager, and a browser-recording subsystem.

## Current Shape

The implemented workflow is:

`outline_writer -> script_writer -> script_converter`

In practice, the repository currently provides:

- A FastAPI backend that runs the workflow, exposes knowledge/task/provider/asset/record APIs, and serves the built frontend
- A Vue 3 + TypeScript frontend for knowledge browsing, pipeline inspection, task execution, provider editing, scene-link management, and recording control
- A Markdown-based knowledge store with supplemental generated metadata for character action/expression data
- Browser automation and recording tooling built around Playwright, CDP screencasting, and FFmpeg offline encoding

This repository is not just a recorder and not just a generic agent framework. The code is organized around WebGal production tasks.

## Repository Layout

```text
WebGalAgent/
├── start.py
├── AGENTS.md
├── .claude/CLAUDE.md
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

Key directories:

- `src/webgal_agent/api/`: FastAPI app, task manager, workflow metadata, and routes
- `src/webgal_agent/browser/`: browser client, CLI demo, recording/session logic, WebGal injection helpers, FFmpeg encoder
- `src/webgal_agent/knowledge/`: file-backed knowledge store and multimodal character-asset description generator
- `src/webgal_agent/tools/`: reusable agent tools such as asset query, file read/write, Live2D model reading, and the test-only expression-motion search helper
- `src/webgal_agent/scene_link/`: scene-link manager that maps generated scene outputs into a WebGal game directory
- `src/frontend/`: Vue UI
- `src/configs/`: runtime YAML configuration
- `data/knowledge/`: knowledge files consumed by the workflow

## Entry Points

Use the project virtualenv Python by default:

```powershell
.\.venv\Scripts\python.exe
```

Main entry points:

- `.\.venv\Scripts\python.exe start.py --dev`
- `.\.venv\Scripts\python.exe start.py`
- `.\.venv\Scripts\python.exe -m webgal_agent`
- `npm run dev --prefix src/frontend`
- `.\.venv\Scripts\python.exe -m webgal_agent.browser.demo record --url <url>`

`start.py` is the convenience launcher:

- `--dev` starts the backend with reload and the frontend Vite dev server together
- Without `--dev`, it builds the frontend first unless `--skip-build` is passed
- It passes `WEBGAL_KNOWLEDGE_DIR=data/knowledge` and `WEBGAL_PROVIDERS_PATH=src/configs/providers.yaml` to the backend

The backend module entry point accepts:

- `--host`
- `--port`
- `--reload`
- `--knowledge-dir`
- `--providers-path`

## Configuration

Current runtime configuration files:

- `src/configs/default.yaml`: application defaults, asset paths, and base LLM defaults
- `src/configs/prompts.yaml`: system prompts and knowledge requirements for the agents
- `src/configs/providers.yaml`: local provider configuration used at runtime
- `src/configs/providers.yaml.sample`: template for a fresh local config
- `src/configs/record.yaml`: defaults for the browser-recording page and API

Environment variables that matter:

- `WEBGAL_KNOWLEDGE_DIR`
- `WEBGAL_PROVIDERS_PATH`
- `WEBGAL_TASK_DIR`
- `WEBGAL_SCENE_LINK_PATH`
- `WEBGAL_SCENE_SOURCE_PATH`

## Workflow

The workflow is defined in `src/webgal_agent/api/workflow_definition.py` and executed by `TaskManager`.

| Step | Agent | Responsibility |
|---|---|---|
| 1 | `outline_writer` | Read the user input and knowledge base, then write the outline |
| 2 | `script_writer` | Expand the outline into a chapter script |
| 3 | `script_converter` | Convert the script into WebGal engine script |

Implementation notes:

- `script_converter` is intentionally tool-limited compared with the other agents
- It receives `read_file`, `query_assets`, `read_model`, and `write_result`
- It does not receive `search_expression_motion` in the formal tool surface
- For character expressions and motions, `script_converter` relies on `read_model` for the legal `motions` and `expressions` list and can consult `expression_motion.md` for human-readable guidance
- When a step is revised by feedback, the previous output is sent back into the model together with the new revision instruction, and both the replaced version and the new version are kept in task history for later comparison

## Knowledge Base

Knowledge files live under `data/knowledge/` and are loaded as file-backed entries.

Current character-knowledge convention:

- `profile.md`: identity, background, personality, relationships
- `expression_motion.md`: human-readable guidance for expressions, motions, and staging suggestions
- `expression_motion.json`: generated action/expression mapping data used by the asset-description pipeline, not the script-conversion knowledge path

The multimodal generator that produces `expression_motion.json` is:

```powershell
.\.venv\Scripts\python.exe -m webgal_agent.knowledge.asset_describer --asset-root data/figure_assets --character-id anon
```

The asset query helper also has a local CLI now:

```powershell
.\.venv\Scripts\python.exe -m webgal_agent.tools.asset_query_cli --asset-type character
```

Important facts:

- `asset_describer` reads character model metadata and writes structured JSON back into `data/knowledge/characters/<角色名>/expression_motion.json`
- The workflow knowledge loader reads Markdown knowledge entries; `expression_motion.json` is no longer injected into the script-conversion knowledge context
- `read_model` now returns only the model's legal `motions` and `expressions` lists
- The standalone `search_expression_motion` helper still exists for testing and experiments, but it is not part of the normal `script_converter` toolchain

## Browser Recording

The recording path is:

`/record page -> /api/record/* -> browser.demo subprocess -> ScreencastRecorder -> FFmpeg offline encode`

Key facts:

- The API does not embed Playwright into FastAPI; it spawns the browser demo CLI as a subprocess
- The main recorder is `src/webgal_agent/browser/screencast.py`
- Captured frames are written to a temporary directory and encoded afterward
- Audio capture is optional and uses WebAudio + PCM/WAV merging
- `--selector auto` tries `#root` first, then `canvas`
- `--duration 0` is only valid when `--stop-on` is also provided
- On Windows, Playwright requires `WindowsProactorEventLoopPolicy`, and the policy is set only in entry points
- `window.saveConfig()` is an async IndexedDB write trigger; recording/config injection code should leave a short delay before touching the same store again

See also: [`src/webgal_agent/browser/README.md`](src/webgal_agent/browser/README.md)

## Frontend Routes

The Vue router currently exposes:

- `/knowledge`
- `/pipeline`
- `/tasks`
- `/providers`
- `/scene-link`
- `/record`

The root route redirects to `/knowledge`.

## Validation

Useful checks:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest
npm run build --prefix src/frontend
```

For quick syntax checks, prefer the smallest relevant file-level check instead of a full rebuild when you only touched one module.

## Documentation Index

- Repo-level agent instructions: [`AGENTS.md`](AGENTS.md)
- Claude guidance: [`.claude/CLAUDE.md`](.claude/CLAUDE.md)
- Browser recording details: [`src/webgal_agent/browser/README.md`](src/webgal_agent/browser/README.md)
- Roadmap and known issues: [`docs/roadmap/issues-and-roadmap.md`](docs/roadmap/issues-and-roadmap.md)
