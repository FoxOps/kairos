"""
Low-level SMTP email sending for Kairos notifications.

Deliberately built on smtplib/email (stdlib) rather than adding a mail
dependency (Flask-Mail etc.) - a single outgoing-mail call is all that's
needed here, triggered by standalone scripts, not by request handling.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(
    *,
    smtp_host: str,
    smtp_port: int,
    from_email: str,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    smtp_username: str | None = None,
    smtp_password: str | None = None,
    smtp_use_tls: bool = True,
    smtp_timeout: int = 10,
) -> None:
    """
    Sends a single email as multipart/alternative (HTML with a plain-text
    fallback, standard practice so clients that don't render HTML still
    get a readable message).

    Takes plain SMTP parameters rather than a config object on purpose:
    app/ code should not depend on scripts/ (scripts/notification_config.py
    holds the env-var-driven config and is the caller here).

    Raises whatever smtplib/socket exception occurs on failure - callers
    are expected to catch per-recipient and continue with the rest of the
    batch rather than letting one failure abort every send.
    """
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=smtp_timeout) as server:
        if smtp_use_tls:
            server.starttls()
        if smtp_username and smtp_password:
            server.login(smtp_username, smtp_password)
        server.sendmail(from_email, [to_email], message.as_string())
