import bcrypt
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError

from app.config.config import settings
from app.services.database_service import DatabaseService


class AuthService:

    @staticmethod
    def hash_password(
        password: str
    ) -> str:

        salt = bcrypt.gensalt()

        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            salt
        )

        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(
        plain_password: str,
        hashed_password: str
    ) -> bool:

        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )

    @staticmethod
    def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:

        to_encode = data.copy()

        expire = datetime.utcnow() + (
            expires_delta
            if expires_delta
            else timedelta(
                hours=settings.JWT_EXPIRY_HOURS
            )
        )

        to_encode["exp"] = expire

        return jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

    @staticmethod
    def decode_access_token(
        token: str
    ) -> Optional[dict]:

        try:

            return jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )

        except JWTError:

            return None

    @classmethod
    def create_user(
        cls,
        name: str,
        email: str,
        password: str
    ) -> dict:

        password_hash = cls.hash_password(password)

        created_at = datetime.utcnow().isoformat()

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO users (
                name,
                email,
                password_hash,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (name, email, password_hash, created_at)
        )

        connection.commit()

        user_id = cursor.lastrowid

        connection.close()

        return {
            "id": user_id,
            "name": name,
            "email": email,
            "created_at": created_at,
        }

    @classmethod
    def get_user_by_email(
        cls,
        email: str
    ) -> Optional[dict]:

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
            """
            SELECT
                id,
                name,
                email,
                password_hash,
                created_at,
                last_login
            FROM users
            WHERE email = ?
            """,
            (email,)
        )

        user = cursor.fetchone()

        connection.close()

        return user

    @classmethod
    def get_user_by_id(
        cls,
        user_id: int
    ) -> Optional[dict]:

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
            """
            SELECT
                id,
                name,
                email,
                created_at,
                last_login
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        connection.close()

        return user

    @classmethod
    def update_last_login(
        cls,
        user_id: int
    ) -> None:

        last_login = datetime.utcnow().isoformat()

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE users
            SET last_login = ?
            WHERE id = ?
            """,
            (last_login, user_id)
        )

        connection.commit()

        connection.close()
