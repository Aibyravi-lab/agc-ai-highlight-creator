from datetime import datetime, timezone
from typing import Optional

from app.services.database_service import DatabaseService


class FeedbackService:

    @classmethod
    def submit(
        cls,
        user_id: int,
        project_id: Optional[int],
        rating: Optional[int],
        thumbs: Optional[str],
        comment: Optional[str],
    ) -> dict:

        conn = DatabaseService.get_connection()

        try:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute(
                """
                INSERT INTO feedback (user_id, project_id, rating, thumbs, comment, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, project_id, rating, thumbs, comment, now),
            )

            conn.commit()

            return {
                "id": cursor.lastrowid,
                "user_id": user_id,
                "project_id": project_id,
                "rating": rating,
                "thumbs": thumbs,
                "comment": comment,
                "created_at": now,
            }

        finally:
            conn.close()

    @classmethod
    def get_all(cls, user_id: int) -> list[dict]:

        conn = DatabaseService.get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, user_id, project_id, rating, thumbs, comment, created_at
                FROM feedback
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "project_id": row[2],
                    "rating": row[3],
                    "thumbs": row[4],
                    "comment": row[5],
                    "created_at": row[6],
                }
                for row in rows
            ]

        finally:
            conn.close()

    @classmethod
    def delete(cls, user_id: int, feedback_id: int) -> bool:

        conn = DatabaseService.get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM feedback WHERE id = ? AND user_id = ?",
                (feedback_id, user_id),
            )

            conn.commit()

            return cursor.rowcount > 0

        finally:
            conn.close()
