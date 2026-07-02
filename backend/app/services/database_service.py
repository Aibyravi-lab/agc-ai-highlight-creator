import sqlite3
from pathlib import Path

from app.config.config import settings


class DatabaseService:

    DB_DIR = Path(
        settings.DATABASE_FOLDER
    )

    DB_PATH = DB_DIR / settings.DATABASE_NAME

    @classmethod
    def initialize(cls):

        cls.DB_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        connection = sqlite3.connect(
            cls.DB_PATH
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (

                job_id TEXT PRIMARY KEY,

                user_id INTEGER,

                status TEXT,

                progress INTEGER,

                message TEXT,

                result TEXT,

                error TEXT,

                created_at TEXT,

                started_at TEXT,

                completed_at TEXT

            )
            """
        )

        # Migration: add user_id to existing jobs tables that predate this column
        try:
            cursor.execute(
                "ALTER TABLE jobs ADD COLUMN user_id INTEGER"
            )
            connection.commit()
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                email TEXT NOT NULL UNIQUE,

                password_hash TEXT NOT NULL,

                created_at TEXT NOT NULL,

                last_login TEXT

            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS history (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                video_name TEXT,

                date TEXT,

                reel_path TEXT,

                highlights_count INTEGER

            )
            """
        )

        # Migration: add user_id to existing history tables that predate this column
        try:
            cursor.execute(
                "ALTER TABLE history ADD COLUMN user_id INTEGER"
            )
            connection.commit()
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                job_id TEXT,

                original_video_name TEXT,

                thumbnail_path TEXT,

                horizontal_reel_path TEXT,

                vertical_reel_path TEXT,

                metadata_json_path TEXT,

                status TEXT DEFAULT 'completed',

                created_at TEXT NOT NULL

            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                project_id INTEGER,

                rating INTEGER,

                thumbs TEXT,

                comment TEXT,

                created_at TEXT NOT NULL

            )
            """
        )

        connection.commit()

        connection.close()

        print(
            "✅ SQLite Database Initialized"
        )

    @classmethod
    def get_connection(cls):

        return sqlite3.connect(
            cls.DB_PATH,
            check_same_thread=False
        )
