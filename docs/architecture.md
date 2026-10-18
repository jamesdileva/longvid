# Automatic Video Editor — Master Architecture

## 1. Project Overview

### 1.1 Purpose

The Automatic Video Editor is a local-first desktop application that analyzes long-form video and automatically identifies, scores, clips, edits, and exports interesting moments.

The system should minimize manual editing while retaining human review as an optional step.

The intended workflow is:

```text
Import Video
    ↓
Media Inspection
    ↓
Audio / Video Processing
    ↓
Transcription
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

### 1.2 Primary Design Goal

The application should answer:

> "Given this long video, what parts are worth turning into clips, and can you turn them into finished videos automatically?"

### 1.3 Initial Target Use Cases

The architecture should support several content types without building separate applications:

* Gaming recordings
* Podcasts
* Interviews
* Commentary
* YouTube videos
* Streaming/VOD recordings
* Tutorials
* Reaction videos
* General recordings

The first implementation should focus on **general-purpose highlight detection**, while the architecture leaves room for specialized detection profiles.

---

# 2. Product Principles

## 2.1 Local First

The default architecture should process media locally.

Benefits:

* No mandatory API keys
* No upload requirements
* Better privacy
* No recurring AI processing costs
* Works offline after dependencies/models are installed
* Large videos do not need to leave the user's machine

Cloud processing can be added later as an optional backend.

## 2.2 Pipeline-Based Architecture

Video processing should not be one giant AI operation.

Instead:

```text
Video
 ↓
Media Metadata
 ↓
Audio Extraction
 ↓
Transcription
 ↓
Scene Detection
 ↓
Audio Analysis
 ↓
Semantic Analysis
 ↓
Candidate Generation
 ↓
Candidate Scoring
 ↓
Editing
 ↓
Export
```

Each stage should be independently testable and replaceable.

## 2.3 AI-Assisted, Not AI-Dependent

Traditional deterministic processing should handle as much as possible.

Examples:

* FFmpeg → media processing
* Whisper → transcription
* VAD → speech detection
* Scene detection → scene boundaries
* Audio analysis → volume/energy
* Computer vision → optional visual events

The LLM should primarily handle **semantic reasoning** rather than basic media manipulation.

## 2.4 Non-Destructive Processing

The original media should never be modified.

All generated assets should exist separately:

```text
source/
working/
analysis/
clips/
exports/
```

---

# 3. Proposed Technology Stack

## 3.1 Desktop Shell

### Electron

Responsibilities:

* Application window
* Native filesystem access
* Process management
* Desktop integration
* Communication with backend
* File selection dialogs
* Application lifecycle

---

# 4. Frontend

## React

UI framework.

## TypeScript

Required for the frontend.

Benefits:

* Strong typing
* Better API contracts
* Easier maintenance
* Safer state management

## Vite

Development/build tooling.

## Recommended UI Architecture

```text
React
 ├── App Shell
 ├── Dashboard
 ├── Projects
 ├── Import
 ├── Processing
 ├── Analysis
 ├── Clip Browser
 ├── Clip Editor
 ├── Export
 └── Settings
```

---

# 5. Backend

## Python

Python should handle the media/AI processing pipeline.

## FastAPI

Responsibilities:

* Project API
* Video import API
* Processing jobs
* Analysis state
* Candidate clips
* Export operations
* Settings
* Pipeline orchestration

The backend should be a local service launched by Electron.

Example:

```text
Electron
   │
   ├── React
   │
   └── FastAPI
          │
          ├── SQLite
          ├── FFmpeg
          ├── Whisper
          ├── OpenCV
          ├── Scene Detection
          └── Local LLM
```

---

# 6. Database

## SQLite

SQLite is the initial database.

No external database server should be required.

Possible future migration path:

```text
SQLite
   ↓
PostgreSQL
```

if the application eventually becomes a server/cloud product.

## ORM

SQLAlchemy 2.x.

## Database Responsibilities

SQLite stores:

* Projects
* Source videos
* Media metadata
* Processing jobs
* Transcripts
* Transcript segments
* Scenes
* Events
* Candidate moments
* Clip definitions
* Editing operations
* Exports
* Application settings

Large binary files should NOT be stored in SQLite.

The database stores paths/references.

---

# 7. Media Processing

## FFmpeg

FFmpeg is the core media engine.

Responsibilities:

* Video metadata
* Audio extraction
* Video cutting
* Encoding
* Resizing
* Aspect ratio conversion
* Audio normalization
* Caption rendering
* Thumbnail generation
* Preview generation
* Final export

The application should invoke FFmpeg through a controlled service rather than scattering shell commands throughout the codebase.

---

# 8. Speech Recognition

## Whisper

Primary transcription engine.

Potential implementation:

* faster-whisper
* Whisper.cpp
* another local Whisper implementation

The abstraction should be:

```python
TranscriptionProvider
```

rather than directly coupling the entire application to one implementation.

Future providers could include:

```text
Whisper
faster-whisper
Whisper.cpp
Cloud transcription
```

---

# 9. Voice Activity Detection

VAD should identify:

* Speech
* Silence
* Long pauses
* Potential dead air

This information can contribute to candidate scoring and automatic trimming.

---

# 10. Scene Detection

Scene detection should identify visual boundaries.

Possible technologies:

* PySceneDetect
* OpenCV
* Custom frame-difference analysis

Scene boundaries can help determine natural clip boundaries.

---

# 11. Audio Analysis

Audio analysis should produce measurable features.

Examples:

```text
volume
RMS energy
peak volume
speech density
silence duration
laughter indicators
sudden audio spikes
```

These features should become normalized events.

Example:

```json
{
  "type": "audio_energy_spike",
  "timestamp": 812.43,
  "strength": 0.91
}
```

---

# 12. Computer Vision

Computer vision should initially be optional.

Potential capabilities:

* Scene changes
* Face detection
* Person detection
* Screen/game detection
* Visual activity
* Camera movement
* Motion intensity

The system should not require expensive vision models for the MVP.

---

# 13. Local LLM

The LLM should analyze structured information rather than raw video whenever possible.

Example input:

```text
Video:
Gaming Session

00:13:42
Player:
"I thought this was impossible..."

00:13:49
Audio energy: HIGH

00:13:51
Player:
"NO WAY!"

00:13:54
Game state:
Victory screen
```

The LLM can classify this as a potential highlight.

Potential local inference providers:

```text
Ollama
llama.cpp
Local model server
```

The application should expose an abstraction:

```python
LLMProvider
```

so the model can be replaced.

---

# 14. AI Analysis Architecture

AI analysis should be divided into multiple responsibilities.

## 14.1 Segment Analyzer

Analyzes transcript/video segments.

## 14.2 Event Detector

Identifies meaningful events.

Examples:

```text
reaction
joke
punchline
surprise
argument
important_statement
victory
failure
reveal
emotional_moment
high_energy
```

## 14.3 Candidate Generator

Combines events into potential clips.

## 14.4 Candidate Scorer

Assigns a score.

Example:

```text
semantic_score: 0.88
audio_score: 0.79
visual_score: 0.91
context_score: 0.83
standalone_score: 0.90

overall_score: 0.86
```

## 14.5 Editor Planner

Determines:

* Start time
* End time
* Crop
* Aspect ratio
* Captions
* Zooms
* Transitions
* Audio treatment

---

# 15. Candidate Clip Model

A candidate clip should be represented independently from the exported file.

Example:

```json
{
  "source_video_id": 42,
  "start_time": 813.2,
  "end_time": 851.8,
  "score": 0.91,
  "reason": "High-energy reaction followed by successful completion",
  "events": [
    "high_energy",
    "reaction",
    "victory"
  ]
}
```

This allows the application to regenerate the clip using different editing settings.

---

# 16. Editing Profiles

The application should support reusable editing profiles.

Examples:

### YouTube Shorts

```text
9:16
<60 seconds
captions
speaker framing
moderate zoom
```

### TikTok

```text
9:16
fast pacing
captions
high-energy emphasis
```

### YouTube

```text
16:9
longer clips
minimal reframing
```

### Clean

```text
original aspect ratio
no captions
no effects
minimal processing
```

Implementations (Phase 10.1) live in `backend/app/editing/`. The catalog is
`clean`, `youtube`, `shorts`, `tiktok`; each profile carries an aspect ratio,
`captions`/`zoom`/`audio_normalization` flags and an optional maximum duration
(60s for the vertical profiles). A profile plus a clip range resolves to a
deterministic editing plan (`plan_version`, `profile`, `source`, `start`, `end`,
`aspect_ratio`, `captions`, `zoom`, `audio_normalization`) that is snapshotted
on the clip for reproducible exports. Applying the plan to pixels (reframing,
captions, audio) lands in later phases.

```http
GET /editing-profiles
```

Phase 10.2 adds automatic trimming (`backend/app/editing/trimming.py`): at clip
creation the padded candidate range is refined against the transcript and the
detected silence runs. A boundary that cuts a sentence is snapped to the
sentence's start/end when within `trim_sentence_tolerance_seconds`; a boundary
sitting in dead air is pulled to the speech edge, keeping only
`trim_pre_roll_seconds` / `trim_post_roll_seconds` of breathing room. The
decision is recorded in the plan's `trim` snapshot (`original_start`,
`original_end`, `sentence_start`, `sentence_end`, `silence_removed_seconds`) so
it stays reproducible.

Phase 10.3 adds captions (`backend/app/editing/captions.py`): transcript
segments overlapping a clip are re-based to the clip start and written as an
SRT sidecar and a styled ASS track (vertical profiles get a larger, higher
style). Clips whose profile requests captions burn the ASS track during
rendering via FFmpeg's `libass`, which forces a video re-encode. The plan marks
`captions` (and `caption_cue_count`); both tracks are downloadable.

```http
GET /clips/{id}/captions/srt
GET /clips/{id}/captions/ass
```

Phase 10.4 adds audio processing (`backend/app/editing/audio.py`): profiles with
`audio_normalization` get a deterministic FFmpeg filter chain — a gentle gate
(`agate`) keeps silence and the noise floor quiet, then EBU R128 loudness
normalization (`loudnorm`) delivers consistent, broadcast-safe levels. The
resolved parameters and the exact chain are snapshotted in the plan's `audio`
entry, and rendering re-encodes audio to AAC when a chain is present.

Phase 11.1/11.2 add aspect-ratio conversion and center cropping
(`backend/app/editing/framing.py`): a profile's target aspect ratio (`original`,
`16:9`, `9:16`, `1:1`) is resolved against the source resolution into a
deterministic center-crop + scale FFmpeg chain, with a mild zoom for
zoom-enabled profiles. It is a no-op when the profile keeps the source ratio or
the source already matches the target. The chain is snapshotted in the plan's
`framing` entry. Subject-tracking / dynamic reframing (roadmap 11.3) is future
work and plugs into the same stage.

---

# 17. Project Structure

Proposed repository:

```text
automatic-video-editor/
│
├── README.md
├── architecture.md
├── implementation-guide.md
├── roadmap.md
├── .gitignore
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       │
│       ├── components/
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── Projects.tsx
│       │   ├── Project.tsx
│       │   ├── Import.tsx
│       │   ├── Processing.tsx
│       │   ├── Clips.tsx
│       │   ├── Editor.tsx
│       │   ├── Export.tsx
│       │   └── Settings.tsx
│       │
│       ├── services/
│       ├── hooks/
│       ├── context/
│       ├── types/
│       └── styles/
│
├── electron/
│   ├── main.js
│   ├── preload.js
│   └── ipc/
│
├── backend/
│   ├── requirements.txt
│   │
│   └── app/
│       ├── main.py
│       │
│       ├── api/
│       │   ├── projects.py
│       │   ├── videos.py
│       │   ├── processing.py
│       │   ├── analysis.py
│       │   ├── clips.py
│       │   ├── exports.py
│       │   └── settings.py
│       │
│       ├── models/
│       ├── schemas/
│       ├── services/
│       │
│       ├── pipeline/
│       │   ├── orchestrator.py
│       │   ├── ingest.py
│       │   ├── audio.py
│       │   ├── transcription.py
│       │   ├── scenes.py
│       │   ├── events.py
│       │   ├── candidates.py
│       │   ├── scoring.py
│       │   └── editing.py
│       │
│       ├── providers/
│       │   ├── transcription/
│       │   ├── llm/
│       │   ├── vision/
│       │   └── audio/
│       │
│       ├── workers/
│       ├── database/
│       └── utils/
│
├── data/
│   ├── projects/
│   ├── cache/
│   ├── models/
│   └── temp/
│
└── tests/
    ├── frontend/
    ├── backend/
    ├── pipeline/
    └── integration/
```

---

# 18. API Architecture

Base URL:

```text
http://127.0.0.1:<port>/api
```

## Projects

```http
GET    /projects
POST   /projects
GET    /projects/{id}
DELETE /projects/{id}
```

## Videos

```http
POST   /projects/{id}/videos
GET    /projects/{id}/videos
GET    /videos/{id}
DELETE /videos/{id}
```

## Processing

```http
POST /videos/{id}/process
GET  /jobs/{id}
POST /jobs/{id}/cancel
```

## Analysis

```http
GET /videos/{id}/transcript
GET /videos/{id}/scenes
GET /videos/{id}/events
GET /videos/{id}/candidates
GET /candidates/{id}/thumbnail
POST /videos/{id}/analyze
```

## Clips

```http
GET    /projects/{id}/clips
GET    /videos/{id}/clips
GET    /clips/{id}
GET    /clips/{id}/file
PATCH  /clips/{id}
DELETE /clips/{id}
POST   /videos/{id}/generate-clips
```

`POST /videos/{id}/generate-clips` creates clip definitions for a candidate
selection (`top5` | `top10` | `all` | `accepted`, or explicit `candidate_ids`)
and queues a `generate_clip` job that renders each to MP4 with FFmpeg.

## Exports

```http
POST /clips/{id}/export
GET  /exports/{id}
GET  /projects/{id}/exports
```

---

# 19. Processing Jobs

Long-running operations must not block HTTP requests.

Example:

```text
POST /videos/42/process
       ↓
job created
       ↓
202 Accepted
       ↓
background worker
       ↓
progress updates
```

Job states:

```text
queued
running
completed
failed
cancelled
```

Pipeline progress:

```text
0%   Ingest
10%  Audio extraction
25%  Transcription
40%  Scene detection
55%  Event detection
70%  Candidate generation
85%  Candidate scoring
100% Analysis complete
```

---

# 20. Real-Time Progress

The UI should receive job progress through:

* WebSocket, or
* Server-Sent Events

Initial implementation may use polling.

Recommended eventual architecture:

```text
FastAPI
   │
   └── WebSocket
          ↓
       React UI
```

---

# 21. File Organization

A project should have an isolated workspace.

```text
project/
│
├── source/
│   └── original.mp4
│
├── media/
│   ├── audio.wav
│   ├── thumbnails/
│   ├── previews/
│   └── candidate-thumbs/
│
├── analysis/
│   ├── transcript.json
│   ├── scenes.json
│   ├── events.json
│   └── candidates.json
│
├── clips/
│   ├── generated/
│   └── previews/
│
└── exports/
    ├── shorts/
    └── youtube/
```

---

# 22. Database Entities

Initial entities:

```text
Project
Video
MediaAsset
ProcessingJob
Transcript
TranscriptSegment
Scene
Event
ClipCandidate
Clip
EditProfile
Export
```

Relationships:

```text
Project
 └── Videos
      ├── ProcessingJobs
      ├── Transcript
      ├── Scenes
      ├── Events
      └── ClipCandidates
             ↓
           Clips
             ↓
          Exports
```

---

# 23. Security / Safety

Because the application executes FFmpeg and potentially other external processes:

* Never directly execute arbitrary user input as shell commands.
* Use subprocess argument arrays rather than shell strings.
* Validate file paths.
* Restrict generated paths to application/project directories where possible.
* Sanitize filenames.
* Never pass raw LLM output directly to a shell.
* Keep local API bound to `127.0.0.1`.
* Validate all API inputs.

---

# 24. Observability

Every processing pipeline should generate logs.

Example:

```text
2026-08-28 13:42:01 INFO  Processing video 42
2026-08-28 13:42:02 INFO  Duration: 01:47:32
2026-08-28 13:42:18 INFO  Transcription complete
2026-08-28 13:42:24 INFO  Detected 147 scenes
2026-08-28 13:42:31 INFO  Detected 83 events
2026-08-28 13:42:37 INFO  Generated 31 candidates
2026-08-28 13:42:40 INFO  Selected top 12 candidates
```

---

# 25. Architecture Evolution

The system should eventually support:

```text
MVP
 ↓
Better AI scoring
 ↓
Specialized content profiles
 ↓
Automatic editing
 ↓
Batch processing
 ↓
Background processing
 ↓
Cloud processing (optional)
 ↓
Multi-user/server mode (optional)
```

The MVP should NOT attempt to implement every AI capability.

---

# 26. Core Architectural Rule

The most important architectural boundary is:

```text
MEDIA PROCESSING ≠ AI REASONING
```

FFmpeg should edit the video.

AI should determine **what should be edited and why**.

This separation allows both sides to improve independently.
