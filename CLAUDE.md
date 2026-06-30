# AI Gaming Highlight Creator (AGC)

## Project Overview

AGC is an AI-powered platform that converts long gaming videos and live stream recordings into short viral highlight clips. Users upload gameplay footage; the system analyzes frames, audio, and scene content using AI to detect highlight moments, score them, and export ready-to-publish clips for YouTube Shorts, Instagram Reels, and TikTok.

## Mission

Enable gamers and streamers worldwide to automatically generate short-form viral content from their gameplay recordings without manual editing, using a fully automated AI pipeline that is fast, affordable, and production-grade.

## Development Philosophy

- **MVP First** — Ship working features before optimizing or expanding scope.
- **Production Ready** — Every feature must be stable enough to deploy, not just demo-ready.
- **Startup Speed** — Move fast. Avoid analysis paralysis. Decide and build.
- **Low Infrastructure Cost** — Prefer local processing, lightweight services, and free tiers where possible.
- **No Over Engineering** — Solve the problem in front of you. Do not design for hypothetical scale.
- **Git Safe** — Never commit broken code. Every commit must leave the repo in a working state.
- **Preserve Existing Business Logic** — Do not remove or rewrite working logic unless explicitly requested.

## Tech Stack

**Backend**
- Python 3.x
- FastAPI + Uvicorn
- Router-based API architecture (`/upload`, `/analysis`, `/frames`, `/vision`, `/highlight`, `/pipeline`, `/clip`, `/editor`, `/history`)
- Service-layer pattern (one service file per domain)

**Frontend**
- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4

**AI**
- OpenAI Whisper — audio transcription and speech event detection
- OpenCV — frame extraction and visual analysis
- PyTorch + Transformers — model inference
- FFmpeg / FFprobe — video processing, frame extraction, clip generation, metadata analysis
- Scoring service — custom highlight scoring pipeline

**Database**
- SQLite via `DatabaseService` (local file-based, zero infrastructure cost)

**Deployment**
- Backend: Uvicorn server, environment config via `.env` and `pydantic-settings`
- Frontend: Next.js production build
- Target: single-server VPS or cloud VM deployment (AGC-007)

## High Level Architecture

```
User Browser (Next.js Frontend)
        │
        ▼  REST API
FastAPI Backend (Uvicorn)
        │
        ├─ Upload Engine        → stores raw video to /uploads
        ├─ Metadata Service     → FFprobe extracts duration, FPS, codec, resolution
        ├─ Frame Service        → FFmpeg extracts 1 FPS frames with timestamps
        ├─ Vision Service       → OpenCV + AI analyzes frames for highlight moments
        ├─ Audio Service        → Whisper transcribes audio, detects audio events
        ├─ Scoring Service      → scores moments by highlight value
        ├─ Pipeline Service     → orchestrates the full detection pipeline
        ├─ Clip Service         → cuts highlight clips via FFmpeg
        ├─ Editor Service       → applies captions, thumbnails, effects
        ├─ Reel / Export        → packages clips for social platforms
        └─ History / Database   → persists job results in SQLite
```

Background jobs run asynchronously via `BackgroundJobService` and `JobService` to keep the API responsive during long AI processing tasks.

## Backend Principles

All business logic lives in the [backend/app/services/](backend/app/services/) layer. Routers in [backend/app/routers/](backend/app/routers/) are thin HTTP adapters only — they validate input, call one or more services, and return the response. No business logic belongs in routers. Each service owns one domain (e.g., `scoring_service.py` owns scoring, `whisper_service.py` owns transcription). Services may call other services but routers may not call routers.

## Frontend Principles

Components in [frontend/components/](frontend/components/) are reusable UI primitives. Pages in [frontend/app/](frontend/app/) compose components and call backend APIs via service modules in [frontend/services/](frontend/services/). API calls belong in service modules, not inside components or pages. Types live in [frontend/types/](frontend/types/) and must be kept in sync with backend response contracts.

## Coding Standards

- Keep functions small and single-purpose.
- Prefer services over inline logic in routers or components.
- Prefer reusable code; extract shared logic into utilities or base services.
- Avoid duplicate logic across services; consolidate into a shared helper if the same logic appears twice.
- All Python code must be type-annotated; all TypeScript code must be strictly typed with no `any`.
- Code must be readable at a glance — clear names, no magic numbers, no unexplained branching.

## Rules for Code Changes

- Never rewrite working code unnecessarily.
- Never remove business logic.
- Never remove AI logic.
- Always preserve backward compatibility with existing API contracts.
- Modify only the functionality explicitly requested.
- Return complete replaceable files whenever a full file rewrite is requested.
- Prefer minimal, targeted changes over broad refactors.

## Git Workflow

- One feature per commit.
- One bug fix per commit.
- Keep commits focused and atomic.
- Never mix refactoring with bug fixes in the same commit.
- Commit messages must describe what changed and why, not just what file was touched.

## Performance Guidelines

- Avoid unnecessary video processing passes; reuse extracted frames and metadata when available.
- Avoid duplicate AI inference; cache results from Whisper and scoring runs within a job.
- Optimize for production throughput: background jobs must not block the API event loop.
- Clean up temporary files after job completion to preserve disk space.

## Security Guidelines

- Never hardcode secrets, API keys, or credentials — use `.env` files and `pydantic-settings`.
- Validate all user-supplied inputs at the API boundary before passing to services.
- Protect filesystem operations: validate file paths, restrict uploads to the designated `/uploads` directory, and reject path traversal attempts.
- Never expose internal stack traces or file paths in API error responses.

## AI Development Guidelines

- Preserve the AI pipeline behavior as implemented in `pipeline_service.py`, `vision_service.py`, `scoring_service.py`, and `whisper_service.py`.
- Preserve scoring logic exactly — highlight scores drive all downstream clip selection decisions.
- Preserve the processing flow: frame extraction → vision analysis → audio analysis → scoring → clip selection → export.
- Never change AI model behavior, scoring weights, or detection thresholds unless explicitly requested.
- When adding new AI capabilities, integrate them as new services that the pipeline calls; do not modify existing detection services.

## Testing Expectations

After every implementation verify:

- Existing functionality still works.
- No API contracts are broken.
- No unnecessary files changed.

---

This file contains permanent project guidance only. Temporary sprint tasks, bugs, and implementation plans must never be stored here.
