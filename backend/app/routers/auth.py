from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from app.services.auth_service import AuthService
from app.dependencies import get_current_user


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
def register(
    body: RegisterRequest
):

    existing = AuthService.get_user_by_email(
        body.email
    )

    if existing:

        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    if len(body.password) < 8:

        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    user = AuthService.create_user(
        name=body.name,
        email=body.email,
        password=body.password
    )

    token = AuthService.create_access_token(
        data={"sub": str(user["id"])}
    )

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "created_at": user["created_at"],
        }
    }


@router.post("/login")
def login(
    body: LoginRequest
):

    user = AuthService.get_user_by_email(
        body.email
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not AuthService.verify_password(
        body.password,
        user["password_hash"]
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    AuthService.update_last_login(user["id"])

    token = AuthService.create_access_token(
        data={"sub": str(user["id"])}
    )

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "created_at": user["created_at"],
            "last_login": user["last_login"],
        }
    }


@router.get("/me")
def me(
    current_user: dict = Depends(get_current_user)
):

    return {
        "success": True,
        "user": {
            "id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"],
            "created_at": current_user["created_at"],
            "last_login": current_user["last_login"],
        }
    }
