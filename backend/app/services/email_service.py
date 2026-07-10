import resend

from app.config.config import settings
from app.services.logger_service import LoggerService


resend.api_key = settings.RESEND_API_KEY


class EmailService:

    @staticmethod
    def _to_html(
        body: str
    ) -> str:

        escaped = (
            body
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        paragraphs = escaped.split("\n\n")

        return "".join(
            f"<p>{paragraph.replace(chr(10), '<br>')}</p>"
            for paragraph in paragraphs
        )

    @staticmethod
    def send(
        to: str,
        subject: str,
        body: str
    ) -> None:

        # Provider is Resend. The message body (which may carry sensitive
        # content such as a password reset link) and the API key are never
        # logged — only sanitized lifecycle events. A send failure must
        # never escape this method — it runs inside a FastAPI
        # BackgroundTask, where an uncaught exception would be lost/unhandled.
        try:

            LoggerService.info("EMAIL queued")

            resend.Emails.send({
                "from": settings.EMAIL_FROM_ADDRESS,
                "to": to,
                "subject": subject,
                "text": body,
                "html": EmailService._to_html(body),
            })

            LoggerService.info("EMAIL delivered")

        except Exception as exc:

            LoggerService.error(
                f"EMAIL failed error_type={exc.__class__.__name__}"
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

    @classmethod
    def send_verification_email(
        cls,
        to: str,
        verify_url: str
    ) -> None:

        cls.send(
            to=to,
            subject="Verify your Vedzovi email address",
            body=(
                "Thanks for signing up for Vedzovi!\n\n"
                f"Verify your email address: {verify_url}\n\n"
                "This link expires in 24 hours. If you didn't create this "
                "account, you can safely ignore this email."
            )
        )
