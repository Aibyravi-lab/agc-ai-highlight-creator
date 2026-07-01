from datetime import datetime

from app.services.database_service import DatabaseService


class HistoryService:

    @classmethod
    def add_history(
        cls,
        video_name: str,
        reel_path: str,
        highlights_count: int,
        user_id: int
    ):

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO history (
                user_id,
                video_name,
                date,
                reel_path,
                highlights_count
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                video_name,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                reel_path,
                highlights_count
            )
        )

        connection.commit()
        connection.close()

    @classmethod
    def get_history(
        cls,
        user_id: int
    ):

        SQL = (
            "SELECT video_name, date, reel_path, highlights_count"
            " FROM history WHERE user_id = ?"
            " ORDER BY date DESC"
        )

        print(
            f"\n[HISTORY DEBUG] SQL:\n  {SQL}"
        )
        print(
            f"[HISTORY DEBUG] Parameters: [{user_id}]"
        )

        connection = DatabaseService.get_connection()

        connection.row_factory = (
            lambda cursor, row: {
                col[0]: row[idx]
                for idx, col in enumerate(
                    cursor.description
                )
            }
        )

        cursor = connection.cursor()

        # Scan all rows first so we can verify user_id population
        raw_cursor = connection.cursor()
        raw_cursor.execute(
            """
            SELECT id, user_id, video_name
            FROM history
            ORDER BY id DESC
            """
        )
        all_rows = raw_cursor.fetchall()
        print(
            f"[HISTORY DEBUG] All rows in history table "
            f"(id, user_id, video_name):"
        )
        for row in all_rows:
            print(f"  {row}")
        if not all_rows:
            print("  (empty table)")

        cursor.execute(SQL, (user_id,))

        history = cursor.fetchall()

        print(
            f"[HISTORY DEBUG] Returned rows: {len(history)}"
        )
        if history:
            print(
                f"[HISTORY DEBUG] First row: {history[0]}"
            )

        connection.close()

        return history
