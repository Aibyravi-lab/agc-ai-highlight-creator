import shutil


class DiskSpaceService:
    """Guards against accepting uploads when the disk is nearly full."""

    MIN_FREE_PERCENT = 10.0

    @classmethod
    def has_sufficient_space(
        cls,
        path: str = "."
    ) -> bool:

        usage = shutil.disk_usage(path)

        free_percent = (usage.free / usage.total) * 100

        return free_percent >= cls.MIN_FREE_PERCENT
