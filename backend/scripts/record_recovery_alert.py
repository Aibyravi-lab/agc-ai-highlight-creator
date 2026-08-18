"""
VED-P1-018: bridges the external self-recovery watchdog (a bash script run
by systemd, outside the backend process) into the existing monitoring_alerts
table via AlertEngineService — so a failed automatic recovery shows up next
to every other production alert instead of starting a second, competing
alert channel.

Called by scripts/self_recovery_watchdog.sh on a best-effort basis: if this
script or the backend venv/database is unavailable, the watchdog logs a
warning and continues — recording an alert must never block or fail a
recovery attempt.

Usage (run from backend/, using the backend venv):
    python scripts/record_recovery_alert.py open backend "message text"
    python scripts/record_recovery_alert.py open frontend "message text"
    python scripts/record_recovery_alert.py resolve backend
    python scripts/record_recovery_alert.py resolve frontend
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.alert_engine_service import AlertEngineService  # noqa: E402

_CHECK_ID_BY_SERVICE = {
    "backend": "self_recovery_backend",
    "frontend": "self_recovery_frontend",
}


def main() -> None:
    args = sys.argv[1:]

    if len(args) < 2 or args[0] not in ("open", "resolve") or args[1] not in _CHECK_ID_BY_SERVICE:
        print(
            "Usage: python scripts/record_recovery_alert.py {open|resolve} {backend|frontend} [message]",
            file=sys.stderr,
        )
        sys.exit(1)

    action, service = args[0], args[1]
    check_id = _CHECK_ID_BY_SERVICE[service]

    if action == "open":
        message = args[2] if len(args) > 2 else f"Automatic recovery for {service} did not succeed."
        AlertEngineService.record_alert(check_id, message)
    else:
        AlertEngineService.resolve_alert(check_id)


if __name__ == "__main__":
    main()
