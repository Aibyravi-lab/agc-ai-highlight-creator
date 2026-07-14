import sqlite3
from datetime import datetime, timezone
from typing import Optional

from app.services.database_service import DatabaseService
from app.services.project_service import ProjectService


class DuplicateFeedbackError(Exception):
    """Raised when a user has already submitted feedback for a project."""


class ProjectNotFoundError(Exception):
    """Raised when the supplied project_id does not exist for this user."""


class FeedbackService:

    # GROW-005: 4-tier rating scale (Bad/Okay/Good/Great). Shared with
    # MissionControlService so the founder dashboard's aggregation stays
    # in sync with the labels the feedback UI actually presents.
    RATING_LABELS: dict[int, str] = {1: "bad", 2: "okay", 3: "good", 4: "great"}
    POSITIVE_RATINGS: tuple[int, ...] = (3, 4)

    @classmethod
    def submit(
        cls,
        user_id: int,
        project_id: Optional[int],
        rating: Optional[int],
        thumbs: Optional[str],
        improvement_area: Optional[str],
        comment: Optional[str],
    ) -> dict:

        # GROW-005: a project_id is client-supplied, so it must be verified
        # to belong to the submitting user before it's trusted — otherwise
        # any authenticated user could attach feedback to someone else's
        # project. Mirrors ProjectService/projects.py's existing "404, don't
        # leak existence" convention for project_ids the caller doesn't own.
        if project_id is not None:
            project = ProjectService.get_project(user_id=user_id, project_id=project_id)
            if project is None:
                raise ProjectNotFoundError("Project not found")

        conn = DatabaseService.get_connection()

        try:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()

            try:
                cursor.execute(
                    """
                    INSERT INTO feedback (
                        user_id, project_id, rating, thumbs, improvement_area, comment, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, project_id, rating, thumbs, improvement_area, comment, now),
                )
            except sqlite3.IntegrityError as exc:
                # sqlite reports the violated columns, not the index name
                # (e.g. "UNIQUE constraint failed: feedback.user_id,
                # feedback.project_id") — matched explicitly so an unrelated
                # integrity failure is never silently reinterpreted as
                # "duplicate". This is the only unique constraint on this
                # table, so this is the only violation this INSERT can hit.
                message = str(exc)
                if "UNIQUE constraint failed" not in message or "feedback.project_id" not in message:
                    raise
                raise DuplicateFeedbackError(
                    "Feedback has already been submitted for this project."
                ) from exc

            conn.commit()

            return {
                "id": cursor.lastrowid,
                "user_id": user_id,
                "project_id": project_id,
                "rating": rating,
                "thumbs": thumbs,
                "improvement_area": improvement_area,
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
                SELECT id, user_id, project_id, rating, thumbs, improvement_area, comment, created_at
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
                    "improvement_area": row[5],
                    "comment": row[6],
                    "created_at": row[7],
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
