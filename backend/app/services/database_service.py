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
