"""
Outgoing email for one-time codes.

Uses Resend's HTTP API when RESEND_API_KEY is set, otherwise SMTP when SMTP_HOST is
set (e.g. Gmail with an app password). With neither, local runs print the email to
the console so codes can still be used during development.
"""
from __future__ import annotations

import json
import logging
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage
from html import escape

from app.config import settings

log = logging.getLogger("ibmode.mail")


class MailNotConfigured(Exception):
    pass


class MailFailed(Exception):
    pass


_PURPOSES = {
    "reset": ("Reset your password", "Use this code to reset your Apex Capital password."),
    "change_email": ("Confirm your new email", "Use this code to confirm this address for your Apex Capital account."),
    "change_password": ("Confirm your password change", "Use this code to change your Apex Capital password."),
}


def send_code(to: str, code: str, purpose: str, minutes: int) -> None:
    title, line = _PURPOSES[purpose]
    footer = f"The code expires in {minutes} minutes. If you didn't ask for it, ignore this email; your account is unchanged."
    text = f"{title}\n\n{line}\n\n    {code}\n\n{footer}\n"
    html = (
        '<div style="font-family:Arial,sans-serif;max-width:440px;margin:auto;color:#111">'
        f'<h2 style="margin:0 0 12px">{escape(title)}</h2><p>{escape(line)}</p>'
        f'<p style="font-size:32px;letter-spacing:8px;font-weight:bold;margin:20px 0">{code}</p>'
        f'<p style="color:#666;font-size:13px">{escape(footer)}</p>'
        '<p style="color:#999;font-size:12px">Apex Capital · Investment Banker Mode (a simulation game)</p></div>'
    )
    send(to, f"{code} is your Apex Capital code", text, html)


def send_notice(to: str, subject: str, text: str) -> None:
    """Best-effort security notice; failures are logged, never raised."""
    try:
        send(to, subject, text)
    except (MailNotConfigured, MailFailed):
        log.warning("Could not send notice to %s", to)


def send(to: str, subject: str, text: str, html: str | None = None) -> None:
    if settings.RESEND_API_KEY:
        _resend(to, subject, text, html)
    elif settings.SMTP_HOST:
        _smtp(to, subject, text, html)
    elif not settings.SERVERLESS:
        log.warning("No email provider configured. Email to %s\nSubject: %s\n%s", to, subject, text)
    else:
        raise MailNotConfigured()


def _sender(default_address: str) -> str:
    return settings.MAIL_FROM or f"Apex Capital <{default_address}>"


def _resend(to: str, subject: str, text: str, html: str | None) -> None:
    body = {"from": _sender("onboarding@resend.dev"), "to": [to], "subject": subject, "text": text}
    if html:
        body["html"] = html
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=json.dumps(body).encode(), method="POST",
        # Resend sits behind Cloudflare, which rejects urllib's default User-Agent.
        headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}", "Content-Type": "application/json",
                 "User-Agent": "ibmode/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except urllib.error.HTTPError as e:
        log.error("Resend rejected email to %s: %s %s", to, e.code, e.read()[:300])
        raise MailFailed() from e
    except Exception as e:
        log.exception("Resend request failed")
        raise MailFailed() from e


def _smtp(to: str, subject: str, text: str, html: str | None) -> None:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = _sender(settings.SMTP_USER), to, subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    try:
        ctx = ssl.create_default_context()
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10, context=ctx)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            server.starttls(context=ctx)
        with server:
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        log.exception("SMTP send to %s failed", to)
        raise MailFailed() from e
