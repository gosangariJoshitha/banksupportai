import smtplib
import ssl
from email.utils import parseaddr
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SMTP_SERVER, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD


class EmailService:
    def send_email(self, recipient, subject, body):
        if not SMTP_EMAIL or not SMTP_PASSWORD:
            return {
                "success": False,
                "message": "Email is not configured. Set SMTP_EMAIL and SMTP_PASSWORD in .env, then restart the app."
            }
        if not recipient or parseaddr(recipient)[1] != recipient.strip():
            return {"success": False, "message": "A valid customer email address is required."}

        message = MIMEMultipart()
        message["From"] = SMTP_EMAIL
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        try:
            password = "".join(SMTP_PASSWORD.split())
            if SMTP_PORT == 465:
                with smtplib.SMTP_SSL(
                    SMTP_SERVER, SMTP_PORT, context=ssl.create_default_context(), timeout=20
                ) as server:
                    server.login(SMTP_EMAIL, password)
                    server.send_message(message)
            else:
                with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as server:
                    server.ehlo()
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                    server.login(SMTP_EMAIL, password)
                    server.send_message(message)
            return {"success": True, "message": "Email notification sent"}
        except (OSError, smtplib.SMTPException) as exc:
            return {"success": False, "message": f"Email delivery failed: {exc}"}
