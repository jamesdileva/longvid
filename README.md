# LongVid

**Local-first automatic video editor.** Point it at a long video and it finds the moments worth clipping — then turns them into finished videos.

LongVid analyzes long-form video (streams, podcasts, gameplay, interviews, VODs), detects candidate highlight moments, scores them, and renders ready-to-publish clips — all locally, with no cloud accounts and no uploads.

## How it works

```text
Import Video
    ↓
Media Inspection (FFprobe)
    ↓
Audio / Video Processing (FFmpeg)
    ↓
Transcription (Whisper)
    ↓
Scene / Event Detection
    ↓
Moment Segmentation
    ↓
Candidate Scoring
    ↓
Clip Generation
    ↓
Automated Editing
    ↓
Preview / Review
    ↓
Export
```

Everything runs on your machine. The original source file is never modified — all generated assets live in project workspaces.

## Architecture

| Layer     | Technology                              |
| --------- | --------------------------------------- |
| Shell     | Electron                                |
| UI        | React + TypeScript + Vite               |
| Backend   | Python 3.11 + FastAPI + Uvicorn         |
| Database  | SQLite + SQLAlchemy 2.x                 |
| Media     | FFmpeg / FFprobe (single service layer) |
| ASR       | Whisper (behind a provider interface)   |
| LLM       | Optional local provider (Ollama, etc.)  |

```text
Electron
 ├── React UI (Vite)
 └── FastAPI (127.0.0.1 only)
        ├── SQLite
        ├── FFmpeg service
        └── provider interfaces (transcription / LLM / vision)
```

The core architectural rule: **media processing ≠ AI reasoning.** FFmpeg edits the
video; AI decides *what* should be edited and *why*.

Full details: [`docs/architecture.md`](docs/architecture.md) ·
[`docs/implementation-guide.md`](docs/implementation-guide.md) ·
[`docs/sprint-roadmap.md`](docs/sprint-roadmap.md)

## Development

Prerequisites:

- Node.js 20+
- Python 3.11
- FFmpeg on PATH

Setup:

```powershell
# Backend (from repo root)
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\pip install -e backend[dev]

# Real local transcription (faster-whisper + model downloads); optional —
# without it, transcription runs against a deterministic synthetic provider
# by setting LONGVID_TRANSCRIPTION_PROVIDER=synthetic
backend\.venv\Scripts\pip install -e backend[whisper]

# Smart reframing (face detection with OpenCV); optional — without it, the
# track_subjects job stores an empty track and clips use a static center crop.
# Set LONGVID_VISION_PROVIDER=synthetic for the deterministic test provider.
backend\.venv\Scripts\pip install -e backend[vision]

# Node workspaces (frontend + electron)
npm install
```

Run in development (Vite dev server + Electron, which launches the backend):

```powershell
npm run dev
```

Run the backend standalone (API on `http://127.0.0.1:8790`):

```powershell
backend\.venv\Scripts\python -m backend.app.main
```

### Commands

| Command                | Description                              |
| ---------------------- | ---------------------------------------- |
| `npm run dev`          | Vite + Electron with backend lifecycle   |
| `npm test`             | Frontend (vitest) + backend (pytest)     |
| `npm run test:backend` | Backend pytest suite                     |
| `npm run test:frontend`| Frontend vitest suite                    |
| `npm run lint`         | Ruff (backend) + TypeScript strict check |
| `npm run format`       | ruff format + ruff check --fix           |
| `npm run build`        | TypeScript typecheck + Vite production build |

## Repository Layout

```text
LongVid/
├── AGENTS.md        # guidelines for contributors and AI agents
├── frontend/        # React + TypeScript UI
├── backend/         # FastAPI service + processing pipeline
├── electron/        # desktop shell (main + preload)
├── docs/            # architecture, implementation guide, roadmap
├── tests/           # cross-package integration tests
└── data/            # local-only: database, project workspaces, caches
```

## Roadmap

Phase-based roadmap in [`docs/sprint-roadmap.md`](docs/sprint-roadmap.md):

1. Architecture & repository foundation
2. Desktop foundation (Electron + React + FastAPI)
3. Database & project management
4. Video ingestion (import, FFprobe, thumbnails)
5. Media pipeline (audio extraction, jobs)
6. Transcription
7. Video understanding (scenes, audio analysis, events)
8. AI highlight detection (local LLM, candidates, scoring)
9. Candidate browser → automatic clipping → editing engine
10. Vertical video, automated editing intelligence, content profiles
11. Batch automation, learning from the user, advanced AI

Milestone 1 (working media tool: import → preview → cut → export) is the near-term goal.
Everything is built so that advanced AI layers can be swapped in without rework.

## Contributing

See [`AGENTS.md`](AGENTS.md) for code style, testing policy, security rules, and the
sprint workflow (plan → scope → implement → verify → commit).

Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.

## License

Not yet determined — the project is pre-alpha.
