# AGENTS.md

Guidelines for AI coding agents (and humans) working in this repository.

## Product

**LongVid** is a local-first desktop application that analyzes long-form video and
automatically identifies, scores, clips, and exports interesting moments.

> Given a long video, what parts are worth turning into clips — and can we turn them
> into finished videos automatically?

The system of record for product and architecture decisions lives in `docs/`:

- `docs/architecture.md` — master architecture (stack, pipeline, data model, security)
- `docs/implementation-guide.md` — build order and per-feature guidance
- `docs/sprint-roadmap.md` — phased roadmap and milestones

If code and docs disagree, raise it — do not silently diverge.

## Stack

| Layer     | Technology                              |
| --------- | --------------------------------------- |
| Shell     | Electron                                |
| UI        | React + TypeScript + Vite               |
| Backend   | Python 3.11 + FastAPI + Uvicorn         |
| Database  | SQLite + SQLAlchemy 2.x                 |
| Media     | FFmpeg / FFprobe (single service layer) |
| ASR       | Whisper (behind a provider interface)   |
| LLM       | Optional local provider (Ollama, etc.)  |

## Repository Layout

```text
LongVid/
├── AGENTS.md            # this file
├── README.md
├── docs/                # architecture, guide, roadmap
├── frontend/            # React + TS + Vite app
├── backend/             # FastAPI service + pipeline
├── electron/            # desktop shell (main + preload)
├── tests/               # cross-package integration tests (later phases)
└── data/                # LOCAL ONLY — projects, DB, caches (gitignored)
```

## Environment Setup

```powershell
# Python backend (use 3.11)
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\pip install -e backend[dev]

# Node (root workspace)
npm install
```

## Common Commands

```powershell
# Development
npm run dev              # Vite dev server + Electron (backend launched by Electron)

# Backend only (wrapper resolves backend/.venv; run from repo root)
npm run backend         # runs API on 127.0.0.1:8790

# Tests
npm test                 # frontend (vitest) + backend (pytest)
npm run test:frontend
npm run test:backend

# Lint / format
npm run lint             # ruff (backend) + tsc (frontend)
npm run format           # ruff format + ruff check --fix

# Build
npm run build            # tsc typecheck + vite build
```

## Code Style

**Python (backend)**

- Ruff for lint + formatting (line length 100).
- Type hints on all public functions. No `Any` without a comment.
- 4-space indentation, docstrings on public modules/classes.
- SQLAlchemy 2.x style: `Mapped` / `mapped_column`, explicit `DeclarativeBase`.
- Never call `subprocess` with `shell=True` or string commands — always argument arrays.
- External tools (FFmpeg, FFprobe, models) go through service classes in
  `backend/app/services/` or provider interfaces in `backend/app/providers/`.

**TypeScript (frontend/electron)**

- Strict mode. No `any` without an `// eslint-disable` + explanation.
- Function components with hooks; no class components.
- API calls live in `frontend/src/services/` — components never `fetch` directly.
- Shared types in `frontend/src/types/`; backend schemas are the contract source.
- Electron: no business logic in main/preload. Thin IPC bridge only; use `contextBridge`.

**General**

- Keep files under ~300 lines; extract modules before they grow.
- No new dependencies without adding them to the relevant `pyproject.toml` /
  `package.json`. Prefer the standard library.
- Comments explain *why*, not *what*. No commented-out code.

## Testing Policy

- Every sprint must end with passing tests for the behavior it adds.
- Backend: `pytest`. Unit tests for pure logic; API tests via `httpx.ASGITransport`.
- Frontend: `vitest` + React Testing Library. One render/behavior test per page/service.
- Do not mock what you can run — but media/AI pipelines use tiny synthetic fixtures.
- Tests are deterministic: fixed timestamps, fixed seeds, no wall-clock dependencies.

## Security Rules (from architecture.md §23 — non-negotiable)

1. Never execute user input as a shell command. Argument arrays only.
2. Never pass raw LLM output to a shell or a file path.
3. Bind the local API to `127.0.0.1` only.
4. Validate and sanitize file paths; keep generated files inside `data/`.
5. Validate all API input with Pydantic schemas before it reaches the database.

## Sprint Workflow

Each sprint follows: **plan → scope → implement → verify (tests) → commit + push**.

- Scope is agreed before implementation starts; changes go through a new commit, not an amend.
- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.
- Definition of Done: scope complete, tests written and passing, lint clean,
  README/AGENTS updated if conventions changed, committed and pushed.

## Data & State

- SQLite stores entities and references, never large binaries. Files live under
  `data/projects/<id>/...` (source, media, analysis, clips, exports).
- All generated assets are non-destructive: the original source file is never modified.
