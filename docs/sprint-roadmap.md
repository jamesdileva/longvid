# Automatic Video Editor — Development Roadmap

# Roadmap Philosophy

Development should proceed from a reliable media pipeline toward increasingly intelligent automation.

The roadmap intentionally avoids making advanced AI a prerequisite for the basic application.

```text
Reliable Media Tool
        ↓
Video Understanding
        ↓
Highlight Detection
        ↓
Automatic Clipping
        ↓
Automatic Editing
        ↓
Personalized Editor
        ↓
Autonomous Video Production
```

---

# Phase 0 — Architecture & Repository

## Sprint 0.1 — Repository Foundation

### Goals

Create the repository and base documentation.

### Deliverables

```text
README.md
architecture.md
implementation-guide.md
roadmap.md
.gitignore
```

Establish:

```text
frontend/
backend/
electron/
tests/
data/
```

### Verification

* Repository initializes.
* Documentation exists.
* Git ignores generated files.

---

# Phase 1 — Desktop Foundation

## Sprint 1.1 — Electron

### Goals

Create desktop shell.

### Deliverables

* Electron window
* Development startup
* Production build configuration
* Safe preload layer

### Verification

Application opens as a desktop window.

---

## Sprint 1.2 — React

### Goals

Create frontend.

### Deliverables

* React
* TypeScript
* Vite
* Router
* Base dark UI
* Application shell

### Initial pages

```text
Dashboard
Projects
Settings
```

---

## Sprint 1.3 — FastAPI

### Goals

Create local backend.

### Deliverables

* FastAPI
* Uvicorn
* `/api/health`
* Electron/backend lifecycle

### Verification

Electron starts backend and frontend communicates successfully.

---

# Phase 2 — Database & Projects

## Sprint 2.1 — SQLite

Create:

```text
projects
videos
processing_jobs
```

---

## Sprint 2.2 — Project Management

Implement:

```text
Create
Read
Update
Delete
```

Projects.

### UI

Project cards should display:

```text
Name
Video count
Clip count
Last modified
Processing state
```

---

## Sprint 2.3 — Workspace System

Create project folders:

```text
source/
media/
analysis/
clips/
exports/
```

### Verification

Creating a project creates a valid isolated workspace.

---

# Phase 3 — Video Ingestion

## Sprint 3.1 — Video Import

Support:

```text
MP4
MOV
MKV
WebM
AVI
```

as practical.

---

## Sprint 3.2 — FFprobe Integration

Extract:

```text
duration
resolution
fps
codec
audio
file size
```

Persist metadata.

---

## Sprint 3.3 — Thumbnail / Preview

Generate:

* Thumbnail
* Short preview
* Media information

### Verification

Imported videos can be previewed in the UI.

---

# Phase 4 — Media Pipeline

## Sprint 4.1 — Audio Extraction

Build audio extraction service.

---

## Sprint 4.2 — FFmpeg Service

Centralize:

```text
probe
extract
cut
encode
thumbnail
preview
```

---

## Sprint 4.3 — Processing Jobs

Introduce background jobs.

UI should display:

```text
Queued
Processing
Completed
Failed
```

with progress.

---

# Phase 5 — Transcription

## Sprint 5.1 — Whisper Integration

Implement local transcription.

---

## Sprint 5.2 — Transcript Database

Store timestamped segments.

---

## Sprint 5.3 — Transcript UI

Build transcript viewer.

Example:

```text
00:12:31  "So here's where everything went wrong."

00:12:37  "Wait..."

00:12:40  "NO WAY!"
```

Clicking transcript text should seek the video.

---

# Phase 6 — Video Understanding

## Sprint 6.1 — Scene Detection

Implement scene detection.

---

## Sprint 6.2 — Audio Analysis

Implement:

* Silence detection
* Audio energy
* Peaks
* Speech density

---

## Sprint 6.3 — Event Model

Create generic event storage.

---

## Sprint 6.4 — Deterministic Event Detection

Initially detect:

```text
silence
audio spike
scene change
speech density
```

No LLM required yet.

---

# Phase 7 — AI Highlight Detection

## Sprint 7.1 — Local LLM Provider

Implement provider abstraction.

Initial target:

```text
Ollama
```

---

## Sprint 7.2 — Semantic Windowing

Combine:

```text
transcript
audio events
scene information
```

into analysis windows.

---

## Sprint 7.3 — Highlight Classification

Ask the model:

```text
Is this interesting?

Why?

What type of moment is it?

How strong is it?

Where should the clip begin/end?
```

---

## Sprint 7.4 — Candidate Generation

Generate candidate clips.

---

## Sprint 7.5 — Candidate Scoring

Implement weighted scoring system.

---

# Phase 8 — Candidate Browser

## Sprint 8.1 — Candidate UI

Display:

```text
thumbnail
title/reason
score
category
duration
timestamp
```

---

## Sprint 8.2 — Candidate Preview

Allow:

```text
Play
Pause
Seek
Accept
Reject
```

---

## Sprint 8.3 — Candidate Filtering

Filters:

```text
All
Best
Funny
Reaction
Important
High Energy
```

Sort:

```text
Score
Timestamp
Duration
```

---

# Phase 9 — Automatic Clipping

## Sprint 9.1 — Clip Model

Create persistent clip definitions.

---

## Sprint 9.2 — Clip Generator

Turn candidates into MP4 files.

---

## Sprint 9.3 — Batch Generation

Allow:

```text
Generate Top 5
Generate Top 10
Generate All
```

---

# Phase 10 — Editing Engine

## Sprint 10.1 — Editing Profiles

Implement:

```text
Clean
YouTube
Shorts
TikTok
```

---

## Sprint 10.2 — Automatic Trimming

Improve:

* Pre-roll
* Post-roll
* Silence removal
* Natural sentence boundaries

---

## Sprint 10.3 — Captions

Implement:

```text
SRT
ASS
Burned captions
```

---

## Sprint 10.4 — Audio Processing

Implement:

* Normalization
* Silence handling
* Basic loudness control

---

# Phase 11 — Vertical Video

## Sprint 11.1 — Aspect Ratio Conversion

Support:

```text
16:9
9:16
1:1
```

---

## Sprint 11.2 — Center Crop

Initial vertical implementation.

---

## Sprint 11.3 — Smart Reframing

Add:

```text
face detection
person tracking
subject tracking
dynamic crop
```

---

# Phase 12 — Automated Editing Intelligence

## Sprint 12.1 — Pacing

Analyze:

```text
speech density
silence
scene duration
```

and make pacing decisions.

---

## Sprint 12.2 — Dynamic Zoom

Detect emphasis moments and apply subtle zooms.

---

## Sprint 12.3 — Caption Intelligence

Support:

* Keyword emphasis
* Important-word highlighting
* Automatic caption timing
* Caption styles

---

## Sprint 12.4 — Hook Detection

Attempt to identify the strongest opening moment.

Potential strategy:

```text
Strongest moment
      ↓
Generate opening hook
      ↓
Context
      ↓
Payoff
```

---

# Phase 13 — Content Profiles

Create specialized analysis profiles.

## Gaming

Detect:

```text
kills
wins
losses
boss kills
reactions
clutches
fails
```

## Podcast

Detect:

```text
strong opinions
arguments
stories
jokes
quotes
surprising statements
```

## Commentary

Detect:

```text
claims
reactions
controversial moments
emotional peaks
```

## General

Use broad semantic scoring.

---

# Phase 14 — Batch Automation

## Sprint 14.1 — Folder Watcher

User selects:

```text
D:/Recordings/
```

Application watches it.

New video:

```text
detected
 ↓
imported
 ↓
analyzed
 ↓
clips generated
```

---

## Sprint 14.2 — Automatic Top Clips

Allow a project configuration:

```text
Automatically create:
Top 5 clips
under 60 seconds
9:16
with captions
```

---

## Sprint 14.3 — Background Processing

Application can process videos while minimized.

---

# Phase 15 — Learning From the User

## Sprint 15.1 — Feedback Collection

Record:

```text
accepted
rejected
edited
exported
```

---

## Sprint 15.2 — Preference Model

Track patterns such as:

```text
User likes:
30–45 sec clips
reaction moments
high-energy audio
minimal effects
```

---

## Sprint 15.3 — Personalized Ranking

Candidate scoring becomes:

```text
content quality
+
general popularity potential
+
user preference
```

---

# Phase 16 — Advanced AI

## Sprint 16.1 — Multimodal Analysis

Allow models to consider:

```text
transcript
audio
frames
scene context
```

together.

---

## Sprint 16.2 — Long-Context Understanding

Understand the video as a whole.

Example:

```text
Setup
 ↓
Build-up
 ↓
Conflict
 ↓
Payoff
```

This can prevent clips from being cut without necessary context.

---

## Sprint 16.3 — Narrative Detection

Detect:

```text
story
setup
punchline
reveal
payoff
reaction
```

and construct clips around complete narrative units.

---

# Phase 17 — Advanced Editor

## Sprint 17.1 — Timeline

Build a lightweight timeline editor.

---

## Sprint 17.2 — Manual Override

User can change:

```text
start
end
crop
captions
effects
audio
```

without losing AI-generated decisions.

---

## Sprint 17.3 — AI Re-edit

User can request:

> "Make this faster."

> "Remove the dead space."

> "Make it more TikTok-style."

> "Keep the reaction but shorten the setup."

The editor regenerates the editing plan.

---

# Phase 18 — Export System

Support:

```text
MP4
H.264
H.265
AAC
```

with presets for:

```text
YouTube
YouTube Shorts
TikTok
Instagram Reels
Local archive
```

---

# Phase 19 — Performance & Reliability

## Goals

Optimize:

* GPU utilization
* CPU utilization
* RAM usage
* Disk usage
* model loading
* FFmpeg encoding
* concurrent jobs

Add:

```text
job queue
resource limits
cancellation
resume
caching
cleanup
```

---

# Phase 20 — Polish

Improve:

* UI
* error messages
* processing progress
* previews
* keyboard shortcuts
* drag/drop
* batch operations
* project management
* settings
* logs
* recovery

---

# Phase 21 — Future Architecture

Possible future capabilities:

```text
Cloud processing
Remote processing PC
GPU worker
Multiple local models
Model marketplace
Plugin system
Custom editing templates
Automatic upload
Social publishing
Team projects
Web interface
```

These should not influence the initial implementation unless they become necessary.

---

# Major Milestones

## Milestone 1 — Working Media Tool

```text
Import
 ↓
Preview
 ↓
Cut
 ↓
Export
```

---

## Milestone 2 — Video Understanding

```text
Import
 ↓
Transcript
 ↓
Scenes
 ↓
Events
```

---

## Milestone 3 — AI Clipper

```text
Video
 ↓
Analysis
 ↓
Candidates
 ↓
Ranking
 ↓
Clips
```

---

## Milestone 4 — Automatic Editor

```text
Video
 ↓
AI analysis
 ↓
Best moments
 ↓
Automatic editing
 ↓
Captions
 ↓
9:16
 ↓
Finished Shorts
```

---

## Milestone 5 — Autonomous Editor

```text
Recording folder
       ↓
Automatic detection
       ↓
Automatic analysis
       ↓
Automatic selection
       ↓
Automatic editing
       ↓
Automatic export
```

The user only reviews the finished results.

---

# Long-Term Vision

The mature system should feel less like traditional video-editing software and more like an **automated post-production agent**.

Instead of:

```text
User → Timeline → Manual editing → Export
```

the experience becomes:

```text
User
  ↓
"Process this recording."
  ↓
AI Video Editor
  ├── watches/analyzes
  ├── understands
  ├── finds moments
  ├── ranks them
  ├── edits them
  ├── captions them
  └── exports them
        ↓
      Results
```

The editor should eventually be capable of producing a set of finished clips that require little or no manual work.

The central product loop becomes:

```text
WATCH
  ↓
UNDERSTAND
  ↓
SELECT
  ↓
EDIT
  ↓
LEARN
  ↓
IMPROVE
```

That loop is the core of the application.
