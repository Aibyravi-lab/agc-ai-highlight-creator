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

        cursor.execute(
            "SELECT video_name, date, reel_path, highlights_count"
            " FROM history WHERE user_id = ?"
            " ORDER BY date DESC",
            (user_id,)
        )

        history = cursor.fetchall()

        connection.close()

        return history
