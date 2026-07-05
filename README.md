# Vedzovi — AI Video Intelligence

**v0.5.0-beta** · Public Beta

> Transform long videos into viral short-form clips — automatically.

Vedzovi is an AI-powered platform that analyzes videos and live stream recordings to detect and export highlight moments as ready-to-publish clips for YouTube Shorts, Instagram Reels, and TikTok. No manual editing required.

---

## Features

- **Automated Upload** — Supports MP4, AVI, MOV, WebM, and MKV with MIME-header validation and deduplication
- **AI Highlight Detection** — Multi-signal scoring pipeline combining motion intensity, scene analysis, audio energy, and visual quality
- **Audio Transcription** — OpenAI Whisper integration for speech and event detection
- **Background Processing** — Non-blocking async job pipeline with real-time progress tracking
- **Clip Export** — FFmpeg-based clip extraction with caption overlay and thumbnail selection
- **Social Packaging** — Output optimized for YouTube Shorts, Instagram Reels, and TikTok
- **User Authentication** — JWT-based auth with bcrypt password hashing and per-user job isolation
- **Project Management** — Organize clips and exports into named projects
- **Job History** — Per-user SQLite-backed history with full result access
- **Observability** — Structured logging, `/health`, `/ready`, and `/metrics` endpoints

---

## Architecture

```
User Browser (Next.js Frontend)
        │
        ▼  HTTPS REST API
FastAPI Backend (Uvicorn)
        │
        ├─ Upload Engine         → MIME validation, dedup, stores to /storage/uploads
        ├─ Metadata Service      → FFprobe: duration, FPS, codec, resolution
        ├─ Frame Service         → FFmpeg: 1 FPS frame extraction with timestamps
        ├─ Vision Service        → OpenCV + AI: frame-level highlight detection
        ├─ Audio Service         → FFmpeg: audio extraction → WAV
        ├─ Whisper Service       → OpenAI Whisper: transcription + speech events
        ├─ Scoring Service       → Multi-signal scoring orchestrator
        │     ├─ audio_scorer    → Audio intensity scoring
        │     ├─ motion_scorer   → Motion and action detection
        │     ├─ scene_scorer    → Scene content scoring
        │     └─ clip_scorer     → Clip quality scoring
        ├─ Pipeline Service      → End-to-end job orchestration
        ├─ Clip Service          → FFmpeg clip cutting
        ├─ Editor Service        → Captions, thumbnails, effects
        ├─ Export Service        → Social-platform packaging
        └─ History / Database    → SQLite: per-user job history and results
```

Background jobs run via `BackgroundJobService` to keep the API responsive during long AI processing tasks.

---

## AI Pipeline

```
Video Upload
     ↓
MIME + Size Validation
     ↓
Duplicate Detection (10-minute dedup window)
     ↓
FFprobe Metadata Extraction
     ↓
FFmpeg Frame Extraction (1 FPS)
     ↓
OpenCV + AI Vision Analysis
     ↓
FFmpeg Audio Extraction → WAV
     ↓
OpenAI Whisper Transcription
     ↓
Multi-Signal Scoring (motion · audio · scene · clip quality)
     ↓
Highlight Ranking
     ↓
FFmpeg Clip Export
     ↓
Caption Overlay + Thumbnail Selection
     ↓
Social Platform Packaging (Shorts · Reels · TikTok)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Backend | Python 3.x, FastAPI, Uvicorn |
| AI — Transcription | OpenAI Whisper |
| AI — Vision | OpenCV, PyTorch, Transformers |
| Video Processing | FFmpeg, FFprobe |
| Database | SQLite (zero-infrastructure, file-based) |
| Authentication | JWT (python-jose), bcrypt |
| Reverse Proxy | Nginx |
| SSL | Let's Encrypt (Certbot) |

---

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- FFmpeg (must be available in PATH)
- Git

Verify prerequisites:

```bash
python --version      # 3.10+
node --version        # 18+
ffmpeg -version
ffprobe -version
```

### Backend Setup

```bash
cd backend
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
```

---

## Environment Variables

### Backend (`backend/.env`)

Copy the example file and fill in values:

```bash
cp backend/.env.example backend/.env
```

Minimum required for local development:

```dotenv
JWT_SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_hex(32))">
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24
FRONTEND_URL=http://localhost:3000
```

For production, also set:

```dotenv
ENVIRONMENT=production
HTTPS_ENABLED=true
PRODUCTION_URL=https://yourdomain.com
WWW_PRODUCTION_URL=https://www.yourdomain.com
```

### Frontend (`frontend/.env.local`)

```bash
cp frontend/.env.example frontend/.env.local
```

Default for local development:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Running Locally

### Start the backend

```bash
cd backend
source venv/bin/activate       # Windows: venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger API docs: `http://localhost:8000/docs`
Health endpoint: `http://localhost:8000/health`

### Start the frontend

```bash
cd frontend
npm run dev
```

Frontend: `http://localhost:3000`

---

## Deployment

See [docs/deploy.md](docs/deploy.md) for the complete production deployment guide covering:

- DNS configuration
- Firewall rules (UFW)
- Nginx reverse proxy setup
- Let's Encrypt SSL (Certbot)
- Backend systemd service
- Frontend (pm2 or systemd)
- Health verification checklist

---

## Screenshots

_Screenshots will be added before the public launch._

---

## Roadmap

| Milestone | Description | Status |
|-----------|-------------|--------|
| AGC-001 | Product planning and architecture | ✅ Complete |
| AGC-002 | Full-stack foundation | ✅ Complete |
| AGC-003 | Video upload engine | ✅ Complete |
| AGC-004 | FFprobe metadata extraction | ✅ Complete |
| AGC-005 | Frame extraction engine | ✅ Complete |
| AGC-021 | Full AI pipeline (vision + Whisper + scoring + clip export) | ✅ Complete |
| AGC-026 | Backend authentication foundation | ✅ Complete |
| AGC-029 | Secure APIs, dashboard, route protection | ✅ Complete |
| AGC-030 | User-scoped history and job isolation | ✅ Complete |
| AGC-034 | Production hardening (observability, security, nginx) | ✅ Complete |
| AGC-035 | Beta release packaging | ✅ Complete |
| AGC-036 | Feedback system, analytics, game profiles | ✅ Complete |
| AGC-102 | AI Explainability Engine and v0.5.0-beta validation | ✅ Complete |
| AGC-103 | v0.5.0-beta release candidate | ✅ Complete |
| AGC-104 | Rate limiting, email verification, password reset | Upcoming |

---

## License

Proprietary. All rights reserved.

---

## Contributing

This project is in private beta. Contribution guidelines will be published at public launch.
