## Vedzovi (AGC) Roadmap

Single source of truth for execution priority. Reflects verified repository
and production evidence as of commit `68cb744` (2026-08-17).

---

## Current Execution Rule

Every engineering task must map to this roadmap. No random scans or fixes
unless production evidence identifies a blocker to the current roadmap
objective.

## Current CTO Priority

Revenue activation and first paying customers.

---

## 1. COMPLETED — Foundation

- **AGC-001** — Product vision, MVP scope, technology decisions, architecture planning
- **AGC-002** — Git setup, FastAPI backend foundation, Swagger docs, frontend bootstrap and frontend/backend connection
- **AGC-003** — Upload engine (router-based upload API, `UploadFile` handling, local `/uploads` storage)
- **AGC-004** — Video processing engine (FFmpeg/FFprobe metadata: duration, FPS, resolution, codec, file size)
- **AGC-005** — AI highlight detection foundation (1 FPS frame extraction engine, `FrameService`, `POST /frames/extract`)

## 2. COMPLETED — Core Product

Delivered incrementally across AGC-006 through AGC-030+, not as single
commits — verified by current service inventory in
[backend/app/services/](backend/app/services/):

- **AGC-006 (Short Clip Generation)** ✅ — superseded and absorbed into the
  full pipeline; confirmed by `clip_service.py`, `editor_service.py`,
  `reel_service.py`, and the "AGC v0.0.9 Stable — automated AI highlight
  pipeline completed" release
- Highlight detection & scoring — `scoring/` package (orchestrator, audio/
  motion/scene/clip/duration sub-scorers), `highlight_service.py`
- CLIP scoring, motion scoring, scene scoring — dedicated scorers under
  `backend/app/services/scoring/`
- Highlight ranking — `highlight_ranking_service.py` (diversity bonus)
- Highlight quality gate — `highlight_quality_gate.py` (VED-P1-007)
- Thumbnail generation/ranking — `backend/app/services/thumbnail/`,
  `thumbnail_rank_service.py`
- Social export infrastructure — `social_export_service.py`,
  `viral_package_service.py`, `result_export_service.py`
- Pipeline / background processing — `pipeline_service.py`,
  `background_job_service.py`, `job_service.py`, `job_storage_service.py`
- Game profiles — `backend/app/services/game_profiles/` (per-game weight
  overrides, auto-detected from filename; SnowRunner, Valorant, CS2, GTA V,
  Rocket League, Forza, PUBG, Minecraft)
- Explainability — `explainability_service.py` (per-signal reasons on every
  ranked highlight)

## 3. COMPLETED — Production Launch

- **AGC-007 (Public MVP Deployment)** ✅ — live in production at
  `vedzovi.com` / `api.vedzovi.com`; not a single event but a continuous
  hardening track: AGC-020 (Production Readiness), AGC v0.4.0-beta (First
  Public Beta Release), AGC-071B (Final production security hardening),
  AGC-072 (Backup & disaster recovery), through VED-DEPLOY-001 (current
  deploy runbook/checklist/verification/rollback/burn-in docs)
- Trusted proxy / security hardening — VED-SEC-001, AGC-066 (SSRF/local
  file access prevention), AGC-065 (arbitrary file deletion prevention),
  AGC-042 (authenticated file access)
- Upload limit handling — VED-P1-004 (Cloudflare 100MB body cap routed
  around; repo-side fix committed at `a0feb27`, 2GB frontend limit raised
  at `7cd74ec`)
- AI worker throughput — VED-P1-003 (fixed global CLIP/Whisper inference
  lock; thread-local models), AGC-043 (bounded global worker pool),
  AGC-044 (hardened SQLite for concurrent access), AGC-041 (isolated job
  storage)
- CI quality gate — VED-P1-001 (`quality-gate.yml`, ESLint scoped to
  changed files)
- Production monitoring — VED-P1-002 (`HealthEngineService`,
  `AlertEngineService`, `HealthHistoryService`, `/admin/health`, weighted
  scoring)
- Operations API — VED-OPS-001 (`ops_service.py`, `/api/v1/ops/*`)
- Maintenance / deployment drain mode — AGC-084 (`maintenance_service.py`)

## 4. COMPLETED — Reliability / Recovery

- **VED-P1-009** — Partial highlight finalization resilience: per-highlight
  failure isolation so one bad highlight doesn't fail the whole job
- **VED-P1-010** — Orphan artifact cleanup on startup
- **VED-P1-011** — Completion recovery: recover completed jobs after a
  terminal commit failure, with a CTO-review follow-up hardening the
  reconciliation path against a crash on `complete_job` failure
- **VED-P1-012** — Register recovered job artifacts so recovered jobs are
  discoverable, not just recovered in-memory
- **VED-P1-016** — Startup reconciliation test coverage hardened
- **VED-P1-017** — Fixed a race where startup cleanup could delete
  artifacts that had just been recovered
- **VED-P1-018-A** — Lazy-load the vision BLIP model per thread (mirrors
  the P1-003 ClipService/WhisperService pattern); removed a live Hugging
  Face Hub round-trip from every backend restart
- **VED-P1-018-B** — Deferred heavy ML package imports (torch/transformers/
  whisper/cv2) out of the `app.main` startup path; reduced `app.main`
  import time from ~7.0s to ~1.25s (~82%)

### Current Production State (snapshot at `68cb744`)

- Deployed commit: `68cb744`
- Restart-to-local-health: 3.265s
- Restart-to-public-health: 3.536s
- Production health: passing (database, FFmpeg, disk all healthy)
- Maintenance mode: OFF
- Active jobs: 0

---

## 5. CURRENT PRIORITY — Revenue Activation

Payment/subscription **code** exists and is production-deployed
(`payment_service.py`, `subscription_service.py`, Razorpay integration at
AGC-059, free-credit system with atomic deduct/refund at AGC-055.1,
subscription expiry enforcement at AGC-068, upgrade UX at AGC-056/056.1,
mock upgrade removed and pricing aligned at AGC-063.2, replay-attack
prevention at AGC-064). What is **not evidenced** in the repository is a
completed end-to-end verification pass or a real paying customer. Treat
every item below as an investigation, not an implementation task, until
proven otherwise:

- 🔴 NOT VERIFIED — verify complete free-user journey (signup → upload →
  first highlight, no payment involved)
- 🔴 NOT VERIFIED — verify upload → processing → highlight → export journey
  end-to-end in production
- 🔴 NOT VERIFIED — verify usage limits (free-credit deduct/refund is
  implemented per AGC-055.1; not confirmed correct under real usage)
- 🔴 NOT VERIFIED — verify subscription/credit/payment implementation
  (Razorpay + `payment_service.py`/`subscription_service.py` exist; no
  evidence of a recent end-to-end payment test)
- 🔴 NOT VERIFIED — verify upgrade flow (UX exists per AGC-056/056.1/063.2;
  not confirmed against live Razorpay checkout)
- 🔴 NOT VERIFIED — verify payment success → entitlement flow (no
  webhook/entitlement-grant code found in `payment_service.py` by a repo
  search — needs direct investigation, not assumption)
- 🔴 NOT VERIFIED — verify paid-user access (does a PRO/paid account
  actually unlock the entitlement `subscription_service.py` claims to
  enforce?)
- 🔴 NOT VERIFIED — verify billing failure/refund correctness (no refund
  logic found in `payment_service.py` by a repo search — needs direct
  investigation)
- 🔴 NOT VERIFIED — verify revenue analytics (conversion funnel
  instrumentation exists — GROW-007, AGC-081, AGC-083 — revenue-specific
  reporting not confirmed)
- 🔴 NOT VERIFIED — perform real-user monetization validation (get one real
  paying customer through the full flow)

## 6. NEXT — Growth & Retention

Instrumentation exists; outcomes are not yet verified. Keep as future work
until revenue activation (Section 5) is proven:

- 🔴 NOT VERIFIED — conversion funnel effectiveness (GROW-007 truth
  signals, AGC-081 analytics funnel, AGC-083 signup conversion analytics
  are implemented; actual conversion outcomes not evidenced)
- 🔴 NOT VERIFIED — in-app feedback loop impact on retention (GROW-005
  feedback loop, GROW-005.1/005.2 reliability fixes implemented; retention
  effect not evidenced)
- 🔴 NOT VERIFIED — homepage trust-proof impact on signup (GROW-004A
  implemented; effect not evidenced)
- 🔴 NOT VERIFIED — founder mission control dashboard usage in day-to-day
  ops (VED-085/086 implemented; not confirmed as the operational default)

## 7. LATER — Scale / Advanced AI

No new speculative items added. Existing forward-looking capability is
limited to what the current architecture already supports (per-game
profiles, modular scorer architecture) — further scale/advanced-AI work
should only be scoped once Section 5 (Revenue Activation) produces a
paying customer to justify it.

---

## Completed Recent Production Releases

| ID | Description | Status |
|----|--------------|--------|
| VED-P1-011 | Recover completed jobs after a terminal commit failure during finalization; CTO-review follow-up hardened reconciliation against a crash on `complete_job` failure | ✅ Deployed |
| VED-P1-012 | Register recovered job artifacts so jobs recovered by P1-011 are discoverable, not just recovered in memory | ✅ Deployed |
| VED-P1-016 | Hardened startup reconciliation test coverage | ✅ Deployed |
| VED-P1-017 | Fixed a race where startup cleanup could delete artifacts that had just been recovered | ✅ Deployed |
| VED-P1-018-A | Lazy-load the vision BLIP model per thread; removed a live Hugging Face Hub round-trip from every backend restart | ✅ Deployed |
| VED-P1-018-B | Deferred heavy ML package imports (torch/transformers/whisper/cv2) out of the `app.main` startup path; restart import time ~7.0s → ~1.25s (~82%) | ✅ Deployed (current HEAD, `68cb744`) |

---

*This roadmap is documentation only. It does not itself authorize or imply
any code, deployment, or infrastructure change.*
