import sqlite3
from pathlib import Path


class DatabaseService:

    DB_DIR = Path("data")

    DB_PATH = DB_DIR / "agc.db"

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