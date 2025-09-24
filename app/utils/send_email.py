import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")


def send_email(subject: str, body: str, to: str, reply_to: Optional[str] = None) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER

    to = to if isinstance(to, list) else [to]
    msg["To"] = ", ".join(to)

    if reply_to:
        msg["Reply-To"] = reply_to

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp_server:
        smtp_server.ehlo()
        smtp_server.starttls()
        smtp_server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        smtp_server.sendmail(GMAIL_USER, to, msg.as_string())
