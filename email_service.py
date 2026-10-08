import smtplib
import ssl
from email.utils import parseaddr
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config


class EmailService:
    def test_connection(self):
        smtp_server = config.SMTP_SERVER or "smtp.gmail.com"
        smtp_port = int(config.SMTP_PORT or 587)
        smtp_email = config.SMTP_EMAIL or ""
        smtp_password = "".join((config.SMTP_PASSWORD or "").split())

        if not smtp_email or not smtp_password:
            return {
                "success": False,
                "message": "Email is missing SMTP_EMAIL or SMTP_PASSWORD in settings or .env."
            }
        try:
            if smtp_port == 465:
                with smtplib.SMTP_SSL(
                    smtp_server, smtp_port, context=ssl.create_default_context(), timeout=10
                ) as server:
                    server.login(smtp_email, smtp_password)
            else:
                with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                    server.ehlo()
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                    server.login(smtp_email, smtp_password)
            return {
                "success": True,
                "message": f"SMTP Authentication successful for {smtp_email}!"
            }
        except smtplib.SMTPAuthenticationError:
            return {
                "success": False,
                "message": "SMTP Authentication Failed: Check email and 16-character Gmail App Password."
            }
        except Exception as exc:
            return {"success": False, "message": f"SMTP Connection error: {exc}"}

    def send_email(self, recipient, subject, body):
        smtp_server = config.SMTP_SERVER or "smtp.gmail.com"
        smtp_port = int(config.SMTP_PORT or 587)
        smtp_email = config.SMTP_EMAIL or ""
        smtp_password = "".join((config.SMTP_PASSWORD or "").split())

        if not smtp_email or not smtp_password:
            return {
                "success": False,
                "message": "Email is not configured. Set SMTP_EMAIL and SMTP_PASSWORD in settings or .env."
            }
        if not recipient or parseaddr(recipient)[1] != recipient.strip():
            return {"success": False, "message": "A valid customer email address is required."}

        message = MIMEMultipart()
        message["From"] = smtp_email
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        try:
            if smtp_port == 465:
                with smtplib.SMTP_SSL(
                    smtp_server, smtp_port, context=ssl.create_default_context(), timeout=20
                ) as server:
                    server.login(smtp_email, smtp_password)
                    server.send_message(message)
            else:
                with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
                    server.ehlo()
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                    server.login(smtp_email, smtp_password)
                    server.send_message(message)
            return {"success": True, "message": "Email notification sent"}
        except (OSError, smtplib.SMTPException) as exc:
            return {"success": False, "message": f"Email delivery failed: {exc}"}

