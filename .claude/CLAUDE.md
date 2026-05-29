# WebGalAgent

Use this repository as a local WebGal workflow workbench, not as a generic agent demo.

## Core Facts

- Main pipeline: `outline_writer -> script_writer -> script_converter`
- Backend: FastAPI
- Frontend: Vue 3 + TypeScript
- Knowledge base: Markdown files under `data/knowledge/` plus generated `expression_motion.json` files
- Browser recording: Playwright + CDP screencast + FFmpeg offline encoding

## Editing Rules

- Use `.venv\Scripts\python.exe` by default
- Read the actual code before editing docs or behavior
- Treat code as the source of truth when docs drift
- Keep changes local and avoid rewriting unrelated files
- Do not revert user work

## Important Entry Points

- `start.py` launches the full app or dev mode
- `src/webgal_agent/__main__.py` starts the backend
- `src/webgal_agent/browser/demo.py` is the browser CLI entry point
- `src/webgal_agent/api/task_manager.py` and `src/webgal_agent/api/task_context.py` drive the workflow

## Knowledge and Script Conversion

- Character identity/background lives in `profile.md`
- Character action/expression guidance lives in `expression_motion.md`
- Generated action/expression mappings live in `expression_motion.json`
- For `script_converter`, prefer the JSON data when both sources exist
- `search_expression_motion` is currently a test/retrieval helper and is not part of the normal `script_converter` tool surface

## Browser Recording Notes

- `ScreencastRecorder` is the primary recorder
- `record.py` launches the browser demo as a subprocess
- `--selector auto` tries `#root` first, then `canvas`
- `--duration 0` only works with `--stop-on`
- On Windows, set `WindowsProactorEventLoopPolicy` only in entry points
- `window.saveConfig()` behaves like an async IndexedDB write trigger; do not read the same store immediately afterward

## Validation

- Syntax check a touched file first when possible
- Use `ruff check .` for lint
- Use `pytest` for behavior changes
- Use `npm run build --prefix src/frontend` when touching the frontend

## Docs To Keep Current

- `README.md`
- `AGENTS.md`
- `src/webgal_agent/browser/README.md`
- `docs/roadmap/issues-and-roadmap.md`
