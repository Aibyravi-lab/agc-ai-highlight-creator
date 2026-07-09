from app.config.config import settings
from app.services.logger_service import LoggerService


class EmailService:

    @staticmethod
    def send(
        to: str,
        subject: str,
        body: str
    ) -> None:

        # No email provider is wired up yet (Resend is planned). Sending is
        # a log statement today; swapping in Resend later means replacing
        # the body of the try block only — no caller changes. The message
        # body is never logged (it may carry sensitive content such as a
        # password reset link), and a send failure must never escape this
        # method — it runs inside a FastAPI BackgroundTask, where an
        # uncaught exception would be lost/unhandled.
        try:

            LoggerService.info(
                f"EMAIL from={settings.EMAIL_FROM_ADDRESS} to={to} "
                f"subject={subject!r} status=sent"
            )

        except Exception as exc:

            LoggerService.error(
                f"EMAIL from={settings.EMAIL_FROM_ADDRESS} to={to} "
                f"subject={subject!r} status=failed error={exc}"
            )

    @classmethod
    def send_password_reset_email(
        cls,
        to: str,
        reset_url: str
    ) -> None:

        cls.send(
            to=to,
            subject="Reset your Vedzovi password",
            body=(
                "We received a request to reset your password.\n\n"
                f"Reset your password: {reset_url}\n\n"
                "This link expires in 30 minutes. If you didn't request "
                "this, you can safely ignore this email."
            )
        )
