import sqlite3
from pathlib import Path

from app.config.config import settings


class DatabaseService:

    DB_DIR = Path(
        settings.DATABASE_FOLDER
    )

    DB_PATH = DB_DIR / settings.DATABASE_NAME

    @classmethod
    def _configure_connection(
        cls,
        connection: sqlite3.Connection
    ) -> sqlite3.Connection:

        connection.execute(
            "PRAGMA journal_mode=WAL"
        )

        connection.execute(
            "PRAGMA busy_timeout=10000"
        )

        connection.execute(
            "PRAGMA foreign_keys=ON"
        )

        return connection

    @classmethod
    def initialize(cls):

        cls.DB_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        connection = cls._configure_connection(
            sqlite3.connect(
                cls.DB_PATH
            )
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
            f"""
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                email TEXT NOT NULL UNIQUE,

                password_hash TEXT NOT NULL,

                created_at TEXT NOT NULL,

                last_login TEXT,

                credits_remaining INTEGER NOT NULL DEFAULT {settings.FREE_CREDITS},

                email_verified INTEGER NOT NULL DEFAULT 0

            )
            """
        )

        # Migration: add credits_remaining to existing users tables that predate this column
        try:
            cursor.execute(
                f"ALTER TABLE users ADD COLUMN credits_remaining "
                f"INTEGER NOT NULL DEFAULT {settings.FREE_CREDITS}"
            )
            connection.commit()
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

        # AGC-070: add email_verified to existing users tables that predate
        # this column. The ALTER TABLE below only succeeds the first time
        # it runs against a pre-AGC-070 database (every later startup hits
        # "duplicate column name" and skips straight to the except branch),
        # so the UPDATE that follows it fires exactly once, and only against
        # rows that existed before email verification was enforced. It
        # backfills every one of those existing users to email_verified=1
        # so current beta users are never locked out of login. Any user
        # inserted after this migration goes through AuthService.create_user,
        # which always explicitly inserts email_verified=0.
        try:
            cursor.execute(
                "ALTER TABLE users ADD COLUMN email_verified "
                "INTEGER NOT NULL DEFAULT 0"
            )
            cursor.execute(
                "UPDATE users SET email_verified = 1"
            )
            connection.commit()
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

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

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL UNIQUE,

                plan TEXT NOT NULL DEFAULT 'FREE',

                status TEXT NOT NULL DEFAULT 'ACTIVE',

                started_at TEXT NOT NULL,

                expires_at TEXT,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL

            )
            """
        )

        # Backfill: give any user that predates the subscriptions table a
        # default FREE/ACTIVE subscription row.
        cursor.execute(
            """
            INSERT INTO subscriptions (
                user_id, plan, status, started_at, expires_at, created_at, updated_at
            )
            SELECT
                id, 'FREE', 'ACTIVE', created_at, NULL, created_at, created_at
            FROM users
            WHERE id NOT IN (SELECT user_id FROM subscriptions)
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                razorpay_order_id TEXT NOT NULL,

                razorpay_payment_id TEXT NOT NULL UNIQUE,

                plan TEXT NOT NULL,

                status TEXT NOT NULL DEFAULT 'PROCESSED',

                created_at TEXT NOT NULL,

                processed_at TEXT NOT NULL,

                FOREIGN KEY (user_id) REFERENCES users(id)

            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_payments_user_id
            ON payments(user_id)
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS password_resets (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                token_hash TEXT NOT NULL UNIQUE,

                created_at TEXT NOT NULL,

                expires_at TEXT NOT NULL,

                used INTEGER NOT NULL DEFAULT 0,

                FOREIGN KEY (user_id) REFERENCES users(id)

            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_password_resets_user_id
            ON password_resets(user_id)
            """
        )

        # AGC-070: email verification tokens, same shape and single-use
        # semantics as password_resets, scoped to a different purpose so
        # the hardened password reset flow above is left untouched.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS email_verifications (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                token_hash TEXT NOT NULL UNIQUE,

                created_at TEXT NOT NULL,

                expires_at TEXT NOT NULL,

                used INTEGER NOT NULL DEFAULT 0,

                FOREIGN KEY (user_id) REFERENCES users(id)

            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_email_verifications_user_id
            ON email_verifications(user_id)
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS password_reset_attempts (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                ip_address TEXT NOT NULL,

                endpoint TEXT NOT NULL,

                created_at TEXT NOT NULL

            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_password_reset_attempts_ip_endpoint
            ON password_reset_attempts(ip_address, endpoint, created_at)
            """
        )

        # AGC-069: generic sliding-window rate limiter shared by every
        # rate-limited endpoint (login, register, upload, pipeline start,
        # payment verify, and — via RateLimitService — password reset).
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rate_limit_attempts (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                key_value TEXT NOT NULL,

                endpoint TEXT NOT NULL,

                created_at TEXT NOT NULL

            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_rate_limit_attempts_key_endpoint
            ON rate_limit_attempts(key_value, endpoint, created_at)
            """
        )

        connection.commit()

        connection.close()

        print(
            "SQLite Database Initialized"
        )

    @classmethod
    def get_connection(cls):

        return cls._configure_connection(
            sqlite3.connect(
                cls.DB_PATH,
                check_same_thread=False
            )
        )
