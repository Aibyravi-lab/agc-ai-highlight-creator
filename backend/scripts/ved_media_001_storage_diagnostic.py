#!/usr/bin/env python3
"""
VED-MEDIA-001 diagnostic: for every row in `projects`, report whether the
on-disk media it references (thumbnail / horizontal reel / vertical reel /
result json) still exists in storage.

READ-ONLY BY CONSTRUCTION:
- Imports only DatabaseService (to resolve the configured DB path/settings)
  and stdlib sqlite3/pathlib. No service that can write, move, or delete a
  file is imported -- no CleanupService, no ProjectService, no
  HistoryService, nothing capable of mutating storage or the database.
- The DB connection is opened via a `file:...?mode=ro` URI (see
  _open_readonly_connection below), not DatabaseService.get_connection().
  This is deliberate: get_connection()/initialize() run `PRAGMA
  journal_mode=WAL` and, on a plain sqlite3.connect(), a missing/misresolved
  path is silently CREATED as a new empty database file -- exactly the kind
  of accidental filesystem mutation this script must never risk when run
  directly against production. mode=ro makes both impossible: a missing
  file raises immediately instead of being created, and any accidental
  write attempt is refused by SQLite itself, not just "avoided by not
  writing any."
- Every filesystem check is `Path.exists()`. Nothing is created, opened for
  writing, renamed, or removed. No INSERT/UPDATE/DELETE anywhere in this
  file.
- Only ever issues one SELECT, against `projects`. Never touches
  `history`, `jobs`, or any other table.

CWD-INDEPENDENT BY DESIGN: DatabaseService.DB_PATH and every
settings.*_FOLDER default (DATABASE_FOLDER="data", JOBS_FOLDER=
"storage/jobs", etc.) are relative paths, resolved against the process's
current working directory -- the production systemd unit sets
WorkingDirectory=.../backend (see backend/scripts/agc-backend.service), so
that is the CWD every path stored in the DB was written against. This
script os.chdir()s to its own backend/ directory (derived from its own
file location, not the caller's CWD) before opening anything, so it
resolves identically whether invoked from the repo root or from backend/.
This chdir affects only this short-lived diagnostic process -- it has no
effect on the running uvicorn service.

This exists to answer, without touching production data: "how many
completed projects currently point at missing media, and is job 98891b68
(user 103, project 98) the only one?" -- see VED-MEDIA-001 forensic report.

Usage (either works, both resolve to the same backend/data/agc.db):
    cd /path/to/repo && python3 backend/scripts/ved_media_001_storage_diagnostic.py
    cd /path/to/repo/backend && python3 scripts/ved_media_001_storage_diagnostic.py
"""

import os
import sqlite3
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from app.services.database_service import DatabaseService  # noqa: E402

ASSET_COLUMNS = (
    "thumbnail_path",
    "horizontal_reel_path",
    "vertical_reel_path",
    "metadata_json_path",
)


def _open_readonly_connection(db_path: Path) -> sqlite3.Connection:

    resolved = db_path.resolve()

    if not resolved.exists():
        raise SystemExit(
            f"ERROR: database not found at {resolved} -- refusing to "
            "proceed (a normal sqlite3.connect() would silently create "
            "an empty file here, which this script must not risk)."
        )

    uri = f"file:{resolved.as_posix()}?mode=ro"

    return sqlite3.connect(uri, uri=True)


def _exists(path: str | None) -> bool | None:

    if not path:
        return None

    return Path(path).exists()


def main() -> int:

    # Deliberately done here, not at module level: chdir as an import-time
    # side effect would silently move the CWD of whatever process imports
    # this module (e.g. a test runner started from the repo root), which
    # is exactly the kind of surprise this script must not cause. Doing it
    # here means it only takes effect when the script is actually executed.
    os.chdir(_BACKEND_DIR)

    connection = _open_readonly_connection(DatabaseService.DB_PATH)

    connection.row_factory = (
        lambda cursor, row: {
            col[0]: row[idx]
            for idx, col in enumerate(cursor.description)
        }
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id, user_id, job_id, status,
            thumbnail_path, horizontal_reel_path,
            vertical_reel_path, metadata_json_path
        FROM projects
        ORDER BY id
        """
    )

    projects = cursor.fetchall()

    connection.close()

    total = len(projects)
    broken = 0

    print(
        f"{'project_id':<10} {'user_id':<8} {'job_id':<38} "
        f"{'status':<10} {'thumb':<6} {'h_reel':<6} {'v_reel':<6} "
        f"{'result':<6} missing_artifacts"
    )

    for project in projects:

        exists = {
            column: _exists(project.get(column))
            for column in ASSET_COLUMNS
        }

        missing = [
            column
            for column, ok in exists.items()
            if ok is False
        ]

        if missing:
            broken += 1

        def _cell(value: bool | None) -> str:
            if value is None:
                return "n/a"
            return "OK" if value else "MISSING"

        print(
            f"{project['id']:<10} {project['user_id']:<8} "
            f"{str(project['job_id']):<38} "
            f"{str(project['status']):<10} "
            f"{_cell(exists['thumbnail_path']):<6} "
            f"{_cell(exists['horizontal_reel_path']):<6} "
            f"{_cell(exists['vertical_reel_path']):<6} "
            f"{_cell(exists['metadata_json_path']):<6} "
            f"{','.join(missing) if missing else '-'}"
        )

    print()
    print(f"RESULT: {broken}/{total} project(s) reference missing media.")

    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
