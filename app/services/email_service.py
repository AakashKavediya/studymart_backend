# app/services/email_service.py
import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import NameEmail
from typing import List

# Load credentials from env
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("SMTP_EMAIL", "aakashkavediya@gmail.com"),
    # ✅ Fallback to empty string prevents Pydantic from crashing if env is missing
    MAIL_PASSWORD=os.getenv("GOOGLE_APP_PASSWORD", ""), 
    MAIL_FROM=os.getenv("SMTP_EMAIL", "aakashkavediya@gmail.com"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_FROM_NAME="StudyBazaar",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_email(subject: str, recipients: List[str], body: str):
    """
    Generic email sender.
    """
    if not conf.MAIL_PASSWORD:
        print("⚠️ Cannot send email: GOOGLE_APP_PASSWORD is not set in .env")
        return

    # Convert strings to NameEmail objects
    name_emails = [NameEmail(name=email.split("@")[0], email=email) for email in recipients]

    message = MessageSchema(
        subject=subject,
        recipients=name_emails,
        body=body,
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        print(f"✅ Email sent to {recipients}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")