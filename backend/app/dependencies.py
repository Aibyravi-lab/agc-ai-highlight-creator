from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

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
