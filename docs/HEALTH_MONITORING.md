# Production Health Monitoring (AGC-073)

## Endpoint

```
GET /health
```

Public, unauthenticated. Returns JSON only. No caching, no side effects.

- `200` when `status` is `"ok"`
- `503` when `status` is `"degraded"`

This is the same `/health` endpoint introduced in AGC-034.2 — AGC-073 adds
richer diagnostics on top of it. The original top-level fields
(`status`, `version`, `environment`, `database`, `ffmpeg`, `uptime_seconds`)
are unchanged so existing consumers (deploy scripts, uptime checks) keep
working without modification.

## Example response

```json
{
  "status": "ok",
  "version": "0.5.0-beta",
  "environment": "production",
  "database": "ok",
  "ffmpeg": "ok",
  "uptime_seconds": 4213,
  "build": {
    "git_commit": "3e58642",
    "git_tag": "v1.0.1-beta"
  },
  "python_version": "3.11.5",
  "ffmpeg_version": "6.0-static",
  "disk": {
    "total_gb": 474.72,
    "used_gb": 310.01,
    "free_gb": 164.71,
    "percent_free": 34.7,
    "status": "healthy"
  },
  "checks": {
    "uploads": "healthy",
    "highlights": "healthy",
    "ffmpeg": "healthy",
    "disk": "healthy",
    "database": "healthy"
  }
}
```

## Field meanings

| Field | Meaning |
|---|---|
| `status` | Overall health: `"ok"` or `"degraded"`. Degraded when the database or ffmpeg checks fail. Drives the HTTP status code (200/503). |
| `version` | Application version string from `APP_VERSION` config. |
| `environment` | `development`, `staging`, or `production`. |
| `database` | `"ok"` / `"error"` — legacy boolean-style DB check (unchanged from AGC-034.2). |
| `ffmpeg` | `"ok"` / `"error"` — legacy boolean-style ffmpeg presence check (unchanged from AGC-034.2). |
| `uptime_seconds` | Seconds since the backend process started. |
| `build.git_commit` | Short git commit hash of the running code, or `"unknown"` if git metadata isn't available (e.g. deployed from a tarball with no `.git`). |
| `build.git_tag` | Nearest git tag, or `"unknown"` if none. |
| `python_version` | Python runtime version (`platform.python_version()`). |
| `ffmpeg_version` | Version string reported by `ffmpeg -version`, or `"unknown"`. |
| `disk.total_gb` / `used_gb` / `free_gb` | Disk usage of the volume the app runs on. |
| `disk.percent_free` | Free disk as a percentage. |
| `disk.status` | `"healthy"` if free disk ≥ 15%, otherwise `"warning"`. A disk warning does **not** flip the overall `status` to `"degraded"` — it's informational, since low disk alone isn't an outage. |
| `checks.uploads` | `"healthy"` if the uploads directory exists and is writable (verified by creating and removing a temp file), else `"unhealthy"`. |
| `checks.highlights` | Same check for the highlights output directory. |
| `checks.ffmpeg` | `"healthy"` if the `ffmpeg` binary is on `PATH`. |
| `checks.disk` | Mirrors `disk.status`. |
| `checks.database` | `"healthy"` if a lightweight `SELECT 1` against SQLite succeeds. |

No field ever contains a filesystem path, environment variable value, secret, or stack trace — checks return only status strings.

## Related endpoints (unchanged)

- `GET /ready` — binary readiness gate for load balancers/orchestrators (`{"ready": true/false, "checks": {...}}`).
- `GET /metrics` — job/user counters for dashboards.

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `status: "degraded"`, `database: "error"` | SQLite file locked, missing, or corrupted | Check the backend process has write access to the data directory; check for a stuck long-running transaction. |
| `status: "degraded"`, `ffmpeg: "error"` | `ffmpeg`/`ffprobe` not installed or not on `PATH` | Reinstall ffmpeg on the host; verify with `ffmpeg -version`. |
| `checks.uploads` / `checks.highlights: "unhealthy"` | Directory missing or not writable by the app user | Check directory ownership/permissions on the VPS; ensure the disk isn't full. |
| `disk.status: "warning"` | Free disk below 15% | Run the cleanup job, clear old job artifacts, or expand the volume. |
| `build.git_commit: "unknown"` | Deployed without a `.git` directory (e.g. built artifact) | Expected in some deploy setups — not an error by itself. |
| Endpoint slow (>100ms) | Disk under heavy I/O, or `ffmpeg -version` subprocess contention | Re-check after load subsides; the endpoint does no heavy work itself. |
| HTTP 503 | `status` is `"degraded"` | Check `database` and `ffmpeg` fields first — those are what drive the status code. |

## Testing

**Local:**

```bash
curl -s http://127.0.0.1:8000/health | jq .
```

**Production:**

```bash
curl -s https://api.vedzovi.com/health | jq .
```

**Swagger:** open `http://127.0.0.1:8000/docs` and expand `GET /health` under the "Observability" tag, then "Try it out".
