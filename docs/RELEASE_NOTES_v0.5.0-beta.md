# AGC v0.5.0-beta — Release Notes

**Release Date:** 2026-07-02
**Release Type:** Public Beta
**Codename:** AI Explainability + Game Profiles

---

## Overview

v0.5.0-beta extends the AGC AI engine with explainability, game-aware scoring, and user feedback infrastructure. The core pipeline from v0.4.0-beta is unchanged. Every ranked highlight now carries a human-readable explanation of why it was selected. Scoring is now tuned per game title using an extensible profile registry. A feedback system allows beta testers to rate highlight quality directly from the dashboard.

---

## Major Features

### AI Explainability Engine

Every ranked highlight now includes an `explanation` block:

- **Per-signal scores** — `clip_score`, `motion_score`, `scene_score`, `audio_score`, `duration_score`
- **Weighted score** — the combined multi-signal score before ranking
- **Ranking score** — the final score after diversity bonus and duplicate penalty
- **Category multiplier** — action-category weight applied from the game profile
- **Synergy multiplier** — bonus applied when multiple signals fire simultaneously
- **Adaptive threshold** — the percentile-based threshold used for this video
- **`reasons[]` array** — human-readable list of only the signals that fired (e.g., `"Audio spike"`, `"Synergy activated"`)

Validated across 6 synthetic test cases and 3 live pipeline highlights. All values verified to 4 decimal places.

### Game Profile System

Per-game scoring weight overrides are now applied automatically based on filename detection:

| Profile | Description |
|---------|-------------|
| SnowRunner | Boosts vehicle and exploration categories |
| Valorant | Boosts audio weight and combat category |
| Counter-Strike 2 | Boosts audio weight and combat category |
| Grand Theft Auto V | Boosts vehicle and combat categories |
| Rocket League | Boosts motion weight and vehicle category |
| Forza | Boosts motion weight and vehicle category |
| PUBG | Boosts audio weight and combat/danger categories |
| Minecraft | Balanced weights |
| Default | Global defaults — applied when no profile matches |

Profiles are defined in `backend/app/services/game_profiles/` and registered in `profile_registry.py`. New profiles can be added without modifying the pipeline.

### Feedback System

Users can rate highlight quality directly from the dashboard:

- Star rating (1–5) per project
- Thumbs up / thumbs down
- Free-text comment (up to 2,000 characters)
- Feedback stored in SQLite and associated with the authenticated user and project
- API: `POST /feedback`

### PostHog Analytics

Optional analytics instrumentation integrated into the frontend:

- Page views and navigation events
- Highlight generation events
- Feedback submission events
- Disabled when `NEXT_PUBLIC_POSTHOG_KEY` is absent — no analytics library loaded in that case

### Benchmark Infrastructure

- `benchmark/snowrunner_benchmark.json` — first real-video benchmark spec with expected timestamps and ±5s tolerance
- Evaluation runner outputs JSON, TXT, Markdown, and CSV reports
- `benchmark/results/` reports are generated at run time and gitignored

---

## AI Validation

A full seven-phase validation was completed prior to this release. See [docs/AI_VALIDATION_REPORT_v0.5.md](AI_VALIDATION_REPORT_v0.5.md) for the complete report.

**AI Readiness Score: 82 / 100**

**Release Recommendation: CONDITIONAL GO**

Key findings:
- Pipeline is fully deterministic — same video always produces identical highlight selections
- Explainability Engine is complete, accurate, and battle-tested
- SnowRunner profile activates correctly from filename and applies correct weights
- Processing ratio: ~0.59× realtime on CPU (253s video processed in ~150s)
- UnicodeEncodeError in evaluation service fixed (Windows compatibility)

---

## Bug Fixes

| Bug | File | Fix |
|-----|------|-----|
| `UnicodeEncodeError` writing benchmark summary on Windows | `evaluation_service.py` | Added `encoding="utf-8"` to all file write calls |

---

## Known Limitations (Carried Forward from v0.4.0-beta)

| Limitation | Detail |
|-----------|--------|
| Single-server deployment | No horizontal scaling or queue-based worker distribution |
| No email verification | User registration does not verify email address |
| No password reset | Password reset flow is not yet implemented |
| No rate limiting | API endpoints are not yet rate-limited per user or IP |
| No video streaming | Uploads are synchronous multipart form uploads |
| No real-time WebSocket progress | Progress is polled via HTTP |
| SQLite only | Database is not replaceable with Postgres in this release |
| No clip preview in UI | No in-browser player; clips require download to view |

## Known Limitations (New in v0.5.0-beta)

| Limitation | Detail |
|-----------|--------|
| No ground-truth benchmark data | P/R/F1 scores reflect alignment with synthetic timestamps, not labelled highlights |
| Single real test video | Only SnowRunner validated end-to-end; GTA V, Valorant, CS2, Rocket League pending real footage |
| Duplicate penalty dead code | `DUPLICATE_PENALTY_WINDOW (30s) < MIN_TIMESTAMP_GAP (45s)` — penalty logic is unreachable; no behavioral impact; tracked for v0.5.1 |
| Profile not passed to ranking | `HighlightRankingService.rank()` receives no profile; ranking bonuses cannot apply until wired; currently harmless as all profiles define empty bonus maps |
| CPU-only inference | No GPU was available; CLIP inference is the bottleneck (~4–6× improvement expected with GPU) |
| Whisper quality on gameplay audio | Transcription unreliable when no clear speech is present; captions only, no highlight impact |

---

## Upgrade Notes

Upgrading from v0.4.0-beta:

1. Pull the latest code.
2. Run `pip install -r requirements.txt` to pick up any new dependencies.
3. No database schema changes — existing SQLite databases are compatible.
4. If using PostHog analytics, add `NEXT_PUBLIC_POSTHOG_KEY` and `NEXT_PUBLIC_POSTHOG_HOST` to `frontend/.env.local`.
5. Rebuild the frontend: `npm run build`.

---

## Future Roadmap

| Feature | Sprint | Priority |
|---------|--------|----------|
| Rate limiting per user and IP | AGC-104 | High |
| Email verification on register | AGC-104 | High |
| Password reset flow | AGC-104 | High |
| Ground-truth benchmark data collection | AGC-104 | High |
| Fix duplicate penalty dead code | AGC-105 | Low |
| Pass profile to ranking service | AGC-105 | Low |
| WebSocket-based progress updates | AGC-106 | Medium |
| Chunked video upload for large files | AGC-106 | Medium |
| GPU inference support | AGC-107 | Medium |
| Multi-server / queue worker support | AGC-110+ | Low |

---

## Checksums

_To be generated at release tag time._

```
SHA256 checksums will be posted here when the release tag is created.
```
