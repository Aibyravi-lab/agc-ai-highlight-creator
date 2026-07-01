# AGC v0.4.0-beta — Release Notes

**Release Date:** 2026-07-01
**Release Type:** Public Beta
**Codename:** Production Hardening

---

## Overview

v0.4.0-beta marks AGC's first public beta release. The core AI highlight pipeline is feature-complete and production-hardened. This release introduces authentication, security hardening, observability, and upload improvements built on top of the complete AI pipeline shipped in earlier sprints.

---

## Major Features

### Complete AI Highlight Pipeline

The full AI pipeline is operational end-to-end:

- **Frame Extraction** — FFmpeg extracts 1 FPS frames with timestamp mapping
- **Vision Analysis** — OpenCV and AI models analyze frames for highlight potential
- **Audio Transcription** — OpenAI Whisper transcribes speech and detects audio events
- **Multi-Signal Scoring** — Orchestrated scoring across motion, audio, scene content, and clip quality
- **Clip Export** — FFmpeg cuts highlight clips from the source video
- **Caption + Thumbnail** — Captions overlaid, best thumbnail selected using quality scoring
- **Social Packaging** — Clips packaged for YouTube Shorts, Instagram Reels, and TikTok

### Authentication and User Isolation

- JWT-based authentication for all protected endpoints
- bcrypt password hashing for secure credential storage
- Per-user job isolation — users can only access their own jobs and results
- User-scoped history and project management

### Background Job Processing

- Upload and pipeline jobs run fully async — the API returns immediately
- Real-time progress tracking available via job status endpoint
- Concurrent job limits enforced per user (default: 2 concurrent jobs)

### Upload Hardening

- MIME-header byte-level validation — file type detected from content, not extension
- Upload deduplication — identical files re-uploaded within a 10-minute window are rejected
- 500 MB upload limit enforced at both Nginx and application layers

### Project Management

- Users can create named projects to organize their highlight exports
- Jobs and results associated with projects

---

## Security Improvements

- **JWT authentication** enforced on all pipeline, history, and project endpoints
- **bcrypt password hashing** — passwords never stored in plaintext
- **Security response headers** on every API response:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: SAMEORIGIN`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
  - `Strict-Transport-Security` (production/HTTPS only)
- **Production CORS** locked to configured allowed origins
- **HTTPS enforcement** — `HTTPS_ENABLED=true` required for production; startup warns if missing
- **Path traversal protection** on all filesystem operations
- **Internal errors not exposed** — user-facing error messages are safe
- **Environment variables** — no hardcoded secrets; all via `.env` and pydantic-settings

---

## Production Hardening

- **Observability endpoints**: `/health`, `/ready`, `/metrics`
- **Structured logging** via `LoggerService` with file output (`backend/logs/agc.log`)
- **Per-request tracing** via `X-Request-ID` response header on every response
- **HTTPS_ENABLED startup guard** — warns when production environment lacks TLS configuration
- **Nginx configuration** with HTTP→HTTPS redirect, 500 MB upload support, 300-second proxy timeouts for long video jobs, and security headers
- **Database initialization** at startup with automatic schema creation
- **FFmpeg validation** at startup — fails fast if FFmpeg is not available

---

## Known MVP Limitations

The following limitations are known and accepted for the v0.4.0-beta release:

| Limitation | Detail |
|-----------|--------|
| Single-server deployment | No horizontal scaling or queue-based worker distribution |
| No email verification | User registration does not verify email address |
| No password reset | Password reset flow is not yet implemented |
| No rate limiting | API endpoints are not yet rate-limited per user or IP |
| No video streaming | Uploads are synchronous multipart form uploads, not chunked streaming |
| Whisper model size | The Whisper model loaded may be `base` or `small` — not configurable via env |
| No real-time WebSocket progress | Progress is polled via HTTP, not pushed via WebSocket |
| SQLite only | Database is not replaceable with Postgres in this release |
| Frame storage not streamed | All frames are written to disk before scoring begins |
| No clip preview in UI | Clip preview requires downloading the clip; no in-browser player yet |
| Frontend in MVP state | Frontend has login, register, and dashboard; full feature UI is in progress |

---

## Future Roadmap

| Feature | Sprint | Priority |
|---------|--------|----------|
| Rate limiting per user and IP | AGC-036 | High |
| Email verification on register | AGC-036 | High |
| Password reset flow | AGC-036 | High |
| Full feature frontend UI | AGC-036 | High |
| WebSocket-based progress updates | AGC-037 | Medium |
| Chunked video upload for large files | AGC-037 | Medium |
| Configurable Whisper model size | AGC-037 | Medium |
| Multi-server / queue worker support | AGC-040+ | Low |
| Postgres support | AGC-040+ | Low |
| Public API documentation site | AGC-040+ | Low |

---

## Upgrade Notes

This is the first public beta release. No upgrade path from prior development builds is required.

For a fresh deployment, follow [docs/deploy.md](deploy.md).

---

## Checksums

_To be generated at release tag time._

```
SHA256 checksums will be posted here when the release tag is created.
```
