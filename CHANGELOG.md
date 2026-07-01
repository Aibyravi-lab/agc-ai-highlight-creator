# Changelog

All notable changes to AGC are documented in this file.

---

## [v0.4.0-beta] — 2026-07-01

### Added
- MIME-header byte-level video validation (MP4, AVI, MOV, WebM, MKV)
- Upload deduplication cache with configurable time window (default: 10 minutes)
- Structured logging via `LoggerService` with file output
- Observability endpoints: `/health`, `/ready`, `/metrics`
- Per-request tracing via `X-Request-ID` response header
- Security headers middleware (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- `HTTPS_ENABLED` startup guard — warns when running production without TLS
- Thumbnail quality scoring pipeline (blur, brightness, contrast, sharpness, composition)
- `viral_package_service` for social platform export packaging
- `result_export_service` for result data export
- `backend/.env.example` — developer onboarding template
- `frontend/.env.example` — developer onboarding template

### Changed
- Scoring pipeline refactored into modular sub-scorers (audio, motion, scene, clip, duration)
- `scoring_service` now orchestrates sub-scorers via dedicated `orchestrator`
- Background job service hardened for concurrent per-user isolation
- Job history scoped per user in SQLite (previously global JSON)
- `requirements.txt` re-encoded as UTF-8 (was UTF-16 LE)

### Fixed
- Authenticated dashboard initialization on first load
- Route protection for unauthenticated users

### Security
- JWT-based authentication on all protected endpoints
- bcrypt password hashing for user accounts
- `bcrypt` and `python-jose` added to `requirements.txt` (were missing)
- Production CORS locked to configured allowed origins
- Filesystem path validation on upload to prevent path traversal

---

## [v0.3.0] — 2026-02

_Spans AGC-029 through AGC-030_

### Added
- JWT authentication system (register, login, token-based sessions)
- Per-user job isolation — users can only access their own jobs and results
- User-scoped job history via SQLite
- Dashboard initialization with authentication state management
- Project management — organize highlight exports into named projects

### Changed
- All pipeline and history endpoints now require authentication
- Dashboard route protected — unauthenticated users redirected to login

### Security
- API endpoints secured with JWT bearer token requirement
- User-scoped data access enforced in all history and pipeline queries

---

## [v0.2.0] — 2025-12

_Spans AGC-024 through AGC-026_

### Added
- Background job pipeline — processing runs async and does not block the API
- Real-time job progress tracking via `progress_service`
- Frontend background job integration with status polling
- Backend authentication foundation (user table, auth router)

### Changed
- Pipeline now fully async via `BackgroundJobService`
- Progress synchronization between backend job state and frontend display

### Fixed
- Production CORS policy blocking frontend requests
- Progress state desync between pipeline and frontend

---

## [v0.1.0] — 2025-09

_Spans AGC-001 through AGC-021_

### Added
- Full-stack foundation: Next.js 16 frontend + FastAPI backend
- Video upload API with multipart form support, file validation, and local storage
- FFprobe metadata extraction (duration, FPS, resolution, codec, file size)
- FFmpeg frame extraction at 1 FPS with timestamp mapping
- OpenCV-based vision analysis for highlight moment detection
- OpenAI Whisper audio transcription and speech event detection
- Multi-signal highlight scoring pipeline
- FFmpeg-based clip generation
- Caption overlay and thumbnail generation
- Social media export (YouTube Shorts, Instagram Reels, TikTok)
- Clip history tracking (JSON-backed, later migrated to SQLite in v0.3.0)
- Router-based API architecture (`/upload`, `/analysis`, `/frames`, `/vision`, `/highlight`, `/pipeline`, `/clip`, `/editor`, `/history`)
- Nginx reverse proxy configuration
- Production deployment guide (`docs/deploy.md`)
