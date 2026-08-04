import secrets

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from app.config.config import settings
from app.services.auth_service import AuthService


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:

    token = credentials.credentials

    payload = AuthService.decode_access_token(token)

    if not payload:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user_id = payload.get("sub")

    if not user_id:

        raise HTTPException(
            status_code=401,
            detail="Invalid token payload"
        )

    user = AuthService.get_user_by_id(int(user_id))

    if not user:

        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user


def require_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    # VED-085: re-checks the DB-fresh is_admin flag on every request (via
    # get_current_user, which always re-fetches the user row) rather than
    # trusting a JWT claim, so revoking admin access takes effect on the
    # very next request with no token reissue needed.

    if not current_user.get("is_admin"):

        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user


# VED-OPS-001: auth for the internal Operations API. Deliberately independent
# of get_current_user/require_admin above — a leaked customer JWT (or an
# admin account) must never grant access to /api/v1/ops/*, and a leaked ops
# key must never grant access to any customer-facing route.
ops_api_key_scheme = APIKeyHeader(
    name="Authorization",
    auto_error=False
)


def verify_ops_api_key(
    authorization: str = Depends(ops_api_key_scheme)
) -> None:

    if not authorization or not authorization.startswith("Bearer "):

        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header"
        )

    provided_key = authorization.removeprefix("Bearer ").strip()

    if not settings.OPS_API_KEY or not secrets.compare_digest(
        provided_key,
        settings.OPS_API_KEY
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid operations API key"
        )
