from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr

from app.config.config import settings
from app.services.auth_service import AuthService
from app.services.email_verification_service import EmailVerificationService
from app.services.password_reset_service import PasswordResetService
from app.services.rate_limit_service import RateLimitService
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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


RATE_LIMIT_MESSAGE = "Too many requests. Please try again later."


GENERIC_FORGOT_PASSWORD_RESPONSE = {
    "success": True,
    "message": (
        "If an account exists for that email, "
        "a password reset link has been sent."
    )
}


GENERIC_RESEND_VERIFICATION_RESPONSE = {
    "success": True,
    "message": (
        "If an account with that email exists and isn't yet verified, "
        "a verification link has been sent."
    )
}


@router.post("/register")
def register(
    body: RegisterRequest,
    background_tasks: BackgroundTasks,
    request: Request
):

    if RateLimitService.is_rate_limited(
        key=request.client.host,
        endpoint="register",
        max_attempts=settings.REGISTER_RATE_LIMIT_MAX_PER_MINUTE,
        window_seconds=60
    ):

        raise HTTPException(
            status_code=429,
            detail=RATE_LIMIT_MESSAGE
        )

    existing = AuthService.get_user_by_email(
        body.email
    )

    if existing:

        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    password_error = AuthService.validate_password_strength(
        body.password
    )

    if password_error:

        raise HTTPException(
            status_code=400,
            detail=password_error
        )

    user = AuthService.create_user(
        name=body.name,
        email=body.email,
        password=body.password
    )

    # AGC-070: registration no longer logs the user in. An access token
    # (and the free credits it would unlock) is only issued after the
    # user verifies their email via /auth/verify-email and logs in.
    background_tasks.add_task(
        EmailVerificationService.send_verification_email,
        user["id"],
        user["email"]
    )

    return {
        "success": True,
        "message": (
            "Registration successful. Please check your email to "
            "verify your account before logging in."
        ),
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "created_at": user["created_at"],
            "credits_remaining": user["credits_remaining"],
            "email_verified": user["email_verified"],
        }
    }


@router.post("/login")
def login(
    body: LoginRequest,
    request: Request
):

    if RateLimitService.is_rate_limited(
        key=request.client.host,
        endpoint="login",
        max_attempts=settings.LOGIN_RATE_LIMIT_MAX_PER_MINUTE,
        window_seconds=60
    ):

        raise HTTPException(
            status_code=429,
            detail=RATE_LIMIT_MESSAGE
        )

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

    # AGC-070: checked after password verification (not before), so a
    # failed login attempt never reveals whether an email is registered
    # but unverified.
    if not user["email_verified"]:

        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in."
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
            "credits_remaining": user["credits_remaining"],
            "email_verified": user["email_verified"],
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
            "credits_remaining": current_user["credits_remaining"],
            "email_verified": current_user["email_verified"],
        }
    }


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    request: Request
):

    # IP throttling runs synchronously, but it depends only on request
    # volume from the caller, not on whether the email exists, so it
    # cannot be used to enumerate accounts.
    if PasswordResetService.is_ip_throttled(
        request.client.host,
        "forgot-password"
    ):

        raise HTTPException(
            status_code=429,
            detail=RATE_LIMIT_MESSAGE
        )

    # The lookup/per-user-throttle/issue/send flow runs after this response
    # is sent, so its outcome (and timing) can never differ based on
    # whether the email exists, is throttled, or a token was issued.
    background_tasks.add_task(
        PasswordResetService.request_reset,
        body.email
    )

    return GENERIC_FORGOT_PASSWORD_RESPONSE


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    request: Request
):

    if PasswordResetService.is_ip_throttled(
        request.client.host,
        "reset-password"
    ):

        raise HTTPException(
            status_code=429,
            detail=RATE_LIMIT_MESSAGE
        )

    password_error = AuthService.validate_password_strength(
        body.new_password
    )

    if password_error:

        raise HTTPException(
            status_code=400,
            detail=password_error
        )

    success = PasswordResetService.reset_password(
        token=body.token,
        new_password=body.new_password
    )

    if not success:

        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )

    return {
        "success": True,
        "message": "Password has been reset successfully"
    }


@router.post("/verify-email")
def verify_email(
    body: VerifyEmailRequest
):

    verified = EmailVerificationService.verify(
        body.token
    )

    if not verified:

        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token"
        )

    return {
        "success": True,
        "message": "Email verified successfully. You can now log in."
    }


@router.post("/resend-verification")
def resend_verification(
    body: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    request: Request
):

    if RateLimitService.is_rate_limited(
        key=request.client.host,
        endpoint="resend-verification",
        max_attempts=settings.RESEND_VERIFICATION_RATE_LIMIT_MAX_PER_HOUR,
        window_seconds=3600
    ):

        raise HTTPException(
            status_code=429,
            detail=RATE_LIMIT_MESSAGE
        )

    # The lookup/already-verified-check/issue/send flow runs after this
    # response is sent, so its outcome can never differ based on whether
    # the email exists or is already verified.
    background_tasks.add_task(
        EmailVerificationService.resend,
        body.email
    )

    return GENERIC_RESEND_VERIFICATION_RESPONSE
