from pathlib import Path

from app.config.config import settings


class MaintenanceService:
    """Live file-existence check for maintenance mode.

    No caching — every call re-reads the filesystem, so toggling the
    sentinel flag (created/removed over SSH via scripts/maintenance.sh)
    takes effect on the very next request without a backend restart.
    """

    MESSAGE = (
        "Vedzovi is upgrading. AI processing is temporarily paused for a "
        "quick update. Your existing projects are safe. "
        "Estimated time: 5–10 minutes."
    )

    RETRY_AFTER_SECONDS = 300

    @classmethod
    def is_maintenance_mode(cls) -> bool:

        try:
            return Path(settings.MAINTENANCE_FLAG_PATH).exists()
        except OSError:
            return False
