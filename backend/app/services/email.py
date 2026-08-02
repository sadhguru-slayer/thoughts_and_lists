# services/email.py

import base64
import logging
import os
import pathlib
import datetime
from email.message import EmailMessage
from core.config import SMTP_USERNAME, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, FRONTEND_URL, ENVIRONMENT
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.discovery_cache.base import Cache
from googleapiclient.errors import HttpError
from schema.enums import OTPPurpose

logger = logging.getLogger(__name__)

# Suppress the noisy file_cache warning and avoid a remote discovery fetch on every send
class _MemoryCache(Cache):
    _data: dict = {}
    def get(self, url):        return self._data.get(url)
    def set(self, url, content): self._data[url] = content

# Module-level singleton so the Gmail service is built once and reused
_gmail_service = None


# ---------------------------------------------------------------------------
# Brand constants
# ---------------------------------------------------------------------------
_BRAND           = "Memo"
_BRAND_COLOR     = "#6c63ff"
_BRAND_GRADIENT  = "linear-gradient(135deg, #6c63ff 0%, #5a52d5 100%)"
_GITHUB_URL      = "https://github.com/sadhguru-slayer"
_FOOTER_NOTE     = 'Built with ♥ by <a href="{url}" style="color:#6c63ff;text-decoration:none;" target="_blank">Sadguru</a>'.format(url=_GITHUB_URL)

# ---------------------------------------------------------------------------
# Frontend deep-link URL builders
# ---------------------------------------------------------------------------

def _task_url(task_id: int) -> str:
    """Return the shareable frontend URL that opens a specific task."""
    base = (FRONTEND_URL or "https://memo.sadguruchenu.in").rstrip("/")
    return f"{base}/tasks?task={task_id}"


def _journal_url(journal_id: int) -> str:
    """Return the shareable frontend URL that opens a specific journal entry."""
    base = (FRONTEND_URL or "https://memo.sadguruchenu.in").rstrip("/")
    return f"{base}/journals/{journal_id}"

# ---------------------------------------------------------------------------
# Shared HTML header/footer snippets
# ---------------------------------------------------------------------------

def _html_header(icon: str, title: str, subtitle: str = "") -> str:
    sub_row = ""
    if subtitle:
        sub_row = f'<div class="header-sub">{subtitle}</div>'

    return f"""
      <div class="header">
        <span class="header-icon">{icon}</span>
        <div class="header-title">{title}</div>
        {sub_row}
      </div>"""


def _html_footer(extra_note: str = "") -> str:
    return f"""
          <hr class="divider"/>
          <div class="footer">
            <p>{extra_note}</p>
            <div class="badge">{_FOOTER_NOTE}</div>
          </div>"""


# ---------------------------------------------------------------------------
# OTP Email
# ---------------------------------------------------------------------------

def generate_email_content(otp_code: str, purpose: OTPPurpose):
    if purpose == OTPPurpose.LOGIN:
        subject  = f"Your {_BRAND} Login Code"
        title    = "Login Verification"
        subtitle = "Use the one-time code below to sign in securely."
        icon     = "🔐"
    elif purpose == OTPPurpose.PASSWORD_RESET:
        subject  = f"Reset your {_BRAND} password"
        title    = "Password Reset"
        subtitle = "Use the code below to reset your password. It expires in 10 minutes."
        icon     = "🔑"
    else:
        subject  = f"Your {_BRAND} OTP Code"
        title    = "Verification Code"
        subtitle = "Use the code below to continue."
        icon     = "✅"

    header = _html_header(icon, title)
    footer = _html_footer(
        f"If you didn't request this, you can safely ignore this email.<br/>"
        f"This is an automated message from {_BRAND}."
    )

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="color-scheme" content="light dark"/>
<title>{subject}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#f0f0f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%}}
  .wrap{{width:100%;background:#f0f0f5;padding:36px 16px}}
  .card{{max-width:480px;margin:0 auto;background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,.10)}}
  .header{{background:{_BRAND_GRADIENT};padding:32px 28px 28px;text-align:center}}
  .header-icon{{font-size:32px;display:block;margin-bottom:4px}}
  .header-title{{font-size:22px;font-weight:700;color:#ffffff;margin-top:4px;line-height:1.3}}
  .body{{padding:32px 28px}}
  .subtitle{{font-size:15px;color:#555;line-height:1.6;margin-bottom:28px}}
  .otp-wrap{{text-align:center;margin:0 0 28px}}
  .otp-label{{font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#aaa;margin-bottom:10px}}
  .otp-box{{display:inline-block;padding:16px 32px;font-size:34px;font-weight:800;letter-spacing:10px;font-family:'Courier New',Courier,monospace;background:#f7f5ff;border:2px solid #e0dbff;border-radius:14px;color:#3d35b0}}
  .note{{font-size:13px;color:#888;text-align:center;line-height:1.6;background:#fafafa;border-radius:10px;padding:14px 16px;border:1px solid #f0f0f0}}
  .divider{{border:none;border-top:1px solid #f0f0f0;margin:24px 0}}
  .footer{{padding:0 0 4px;text-align:center}}
  .footer p{{font-size:12px;color:#bbb;line-height:1.7}}
  .footer a{{color:{_BRAND_COLOR};text-decoration:none}}
  .badge{{display:inline-block;margin-top:12px;font-size:11px;color:#bbb;letter-spacing:.3px}}

  @media only screen and (max-width:480px){{
    .wrap{{padding:20px 10px}}
    .header{{padding:24px 20px 20px}}
    .header-title{{font-size:20px}}
    .body{{padding:24px 20px}}
    .otp-box{{font-size:26px;letter-spacing:6px;padding:14px 22px}}
  }}
  @media (prefers-color-scheme:dark){{
    body,.wrap{{background:#0d0d14!important}}
    .card{{background:#1a1a2e!important;box-shadow:0 8px 40px rgba(0,0,0,.5)!important}}
    .body{{background:#1a1a2e!important}}
    .subtitle{{color:#aaa!important}}
    .otp-box{{background:#16213e!important;border-color:#3d35b0!important;color:#a89dff!important}}
    .note{{background:#12122a!important;border-color:#2a2a4a!important;color:#888!important}}
    .divider{{border-color:#2a2a4a!important}}
    .footer p{{color:#555!important}}
  }}
</style>
</head>
<body>
<div class="wrap">
  <table width="100%" role="presentation" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <div class="card">
        {header}
        <div class="body">
          <p class="subtitle">{subtitle}</p>
          <div class="otp-wrap">
            <div class="otp-label">Your one-time code</div>
            <div class="otp-box">{otp_code}</div>
          </div>
          <div class="note">
            ⏱ This code expires in <strong>10 minutes</strong>.<br/>
            🔒 Never share this with anyone.
          </div>
          {footer}
        </div>
      </div>
    </td></tr>
  </table>
</div>
</body>
</html>"""

    text_body = f"""{_BRAND} — {title}

{subtitle}

Your OTP: {otp_code}

This code expires in 10 minutes. Do not share it with anyone.

— Built by Sadguru ({_GITHUB_URL}) · {_BRAND}
"""
    return subject, text_body, html_body


# ---------------------------------------------------------------------------
# Reminder Email
# ---------------------------------------------------------------------------

def _build_reminder_html(
    title: str,
    subtitle: str,
    body_text: str,
    icon: str = "\U0001f514",
    cta_url: str = "",
    cta_label: str = "",
    task_title: str = "",
    is_task: bool = False,
) -> str:
    # For task emails, the title appears in the card body — suppress the header subtitle
    header = _html_header(icon, title, subtitle="" if is_task else subtitle)
    footer = _html_footer(
        f"You're receiving this because reminders are enabled in your {_BRAND} settings.<br/>"
        "You can update your preferences anytime from the app."
    )

    # ── Task card: clickable title + description block ──────────────────────
    if is_task and task_title:
        if cta_url:
            title_html = (
                f'<a href="{cta_url}" target="_blank" '
                f'style="font-size:18px;font-weight:800;color:#3d35b0;text-decoration:none;'
                f'line-height:1.3;display:block;word-break:break-word;">'
                f'\U0001f4cc {task_title}</a>'
            )
        else:
            title_html = (
                f'<span style="font-size:18px;font-weight:800;color:#3d35b0;line-height:1.3;'
                f'display:block;word-break:break-word;">\U0001f4cc {task_title}</span>'
            )
        desc_html = (
            f'<p style="margin:10px 0 0;font-size:14px;color:#555;line-height:1.65;">{body_text}</p>'
            if body_text else ""
        )
        view_btn = (
            f'<div style="margin-top:18px;">'
            f'<a href="{cta_url}" target="_blank" '
            f'style="display:inline-block;padding:10px 22px;background:{_BRAND_GRADIENT};'
            f'color:#fff;font-size:13px;font-weight:700;border-radius:10px;text-decoration:none;'
            f'letter-spacing:.3px;box-shadow:0 4px 14px rgba(108,99,255,.28);">'
            f'Open Task \u2192</a></div>'
        ) if cta_url else ""

        content_html = f"""
          <div style="background:linear-gradient(135deg,#f7f5ff,#eef0ff);
               border-left:4px solid {_BRAND_COLOR};border-radius:12px;
               padding:20px 22px;">
            {title_html}
            {desc_html}
            {view_btn}
          </div>"""
    else:
        # ── Generic message box (journal / other) ──────────────────────────
        content_html = (
            f'<div style="background:linear-gradient(135deg,#f7f5ff,#eef0ff);'
            f'border-left:4px solid {_BRAND_COLOR};border-radius:12px;'
            f'padding:20px 22px;font-size:15px;color:#333;line-height:1.7;">'
            f'{body_text}</div>'
        )
        # CTA button for journal / generic
        if cta_url and cta_label:
            content_html += (
                f'<div style="text-align:center;margin:22px 0 4px;">'
                f'<a href="{cta_url}" target="_blank" '
                f'style="display:inline-block;padding:13px 28px;background:{_BRAND_GRADIENT};'
                f'color:#fff;font-size:14px;font-weight:700;border-radius:12px;text-decoration:none;'
                f'letter-spacing:.3px;box-shadow:0 4px 14px rgba(108,99,255,.35);">'
                f'{cta_label}</a></div>'
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="color-scheme" content="light dark"/>
<title>{title}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#f0f0f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%}}
  .wrap{{width:100%;background:#f0f0f5;padding:36px 16px}}
  .card{{max-width:480px;margin:0 auto;background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,.10)}}
  .header{{background:{_BRAND_GRADIENT};padding:32px 28px 28px;text-align:center}}
  .header-icon{{font-size:36px;display:block;margin-bottom:4px}}
  .header-title{{font-size:22px;font-weight:700;color:#ffffff;margin-top:4px;line-height:1.3}}
  .header-sub{{font-size:14px;color:rgba(255,255,255,.82);margin-top:6px}}
  .body{{padding:32px 28px}}
  .divider{{border:none;border-top:1px solid #f0f0f0;margin:24px 0}}
  .footer{{padding:0 0 4px;text-align:center}}
  .footer p{{font-size:12px;color:#bbb;line-height:1.7}}
  .footer a{{color:{_BRAND_COLOR};text-decoration:none}}
  .badge{{display:inline-block;margin-top:12px;font-size:11px;color:#bbb;letter-spacing:.3px}}

  @media only screen and (max-width:480px){{
    .wrap{{padding:20px 10px}}
    .header{{padding:24px 20px 20px}}
    .header-title{{font-size:19px}}
    .body{{padding:24px 20px}}
  }}
  @media (prefers-color-scheme:dark){{
    body,.wrap{{background:#0d0d14!important}}
    .card{{background:#1a1a2e!important;box-shadow:0 8px 40px rgba(0,0,0,.5)!important}}
    .body{{background:#1a1a2e!important}}
    .divider{{border-color:#2a2a4a!important}}
    .footer p{{color:#555!important}}
  }}
</style>
</head>
<body>
<div class="wrap">
  <table width="100%" role="presentation" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <div class="card">
        {header}
        <div class="body">
          {content_html}
          {footer}
        </div>
      </div>
    </td></tr>
  </table>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Gmail send helpers
# ---------------------------------------------------------------------------

def _get_gmail_service():
    global _gmail_service
    if _gmail_service is not None:
        return _gmail_service
    creds = Credentials(
        token=None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        client_id=GMAIL_CLIENT_ID,
        client_secret=GMAIL_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    _gmail_service = build("gmail", "v1", credentials=creds, cache=_MemoryCache())
    logger.info("Gmail service initialised and cached.")
    return _gmail_service


# Folder where dev email previews are written (relative to this file's package root)
_DEV_PREVIEW_DIR = pathlib.Path(__file__).resolve().parent.parent / "email_previews"


def _dev_save_html(subject: str, to_email: str, html_body: str, log_label: str) -> str:
    """Write email HTML to disk and return the file path (dev only)."""
    _DEV_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = log_label.lower().replace(" ", "_")
    filename = f"{ts}_{safe_label}.html"
    filepath = _DEV_PREVIEW_DIR / filename
    filepath.write_text(html_body, encoding="utf-8")
    return str(filepath)


def _send_via_gmail(to_email: str, subject: str, text_body: str, html_body: str, log_label: str = "Email"):
    logger.info("==================== EMAIL SEND DEBUG ====================")
    logger.info("ENVIRONMENT Mode: %s", ENVIRONMENT)
    logger.info("Subject: %s | To: %s | Label: %s", subject, to_email, log_label)
    logger.info("Generated HTML Content:\n%s", html_body)
    logger.info("==========================================================")

    # ── Dev mode: write to disk instead of hitting Gmail ──────────────────
    if ENVIRONMENT == "development":
        filepath = _dev_save_html(subject, to_email, html_body, log_label)
        logger.info(
            "[DEV] %s NOT sent (dev mode). HTML preview saved → %s",
            log_label, filepath
        )
        return

    # ── Production: send via Gmail API ────────────────────────────────────
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_USERNAME
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    service = _get_gmail_service()
    encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": encoded}).execute()
    logger.info("%s SENT via Gmail API to %s | Message ID: %s", log_label, to_email, result.get("id"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def send_otp_email(to_email: str, otp_code: str, purpose: OTPPurpose):
    logger.info("Sending OTP email to %s for purpose %s", to_email, purpose)
    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET or not GMAIL_REFRESH_TOKEN:
        logger.error("Gmail credentials not set in .env (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, or GMAIL_REFRESH_TOKEN missing)")
        return
    

    subject, text_body, html_body = generate_email_content(otp_code, purpose)
    try:
        _send_via_gmail(to_email, subject, text_body, html_body, log_label="OTP Email")
    except HttpError as error:
        logger.error("Gmail API error sending OTP: %s", error)
    except Exception as e:
        logger.error("Failed to send OTP email: %s", e)


def send_reminder_email(
    to_email: str,
    subject: str,
    title: str,
    subtitle: str,
    body_text: str,
    icon: str = "\U0001f514",
    task_id: int | None = None,
    journal_id: int | None = None,
    cta_label: str = "",
):
    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET or not GMAIL_REFRESH_TOKEN:
        logger.error("Gmail credentials not set in .env")
        return

    cta_url = ""
    is_task = False
    task_title_for_card = ""

    if task_id:
        cta_url = _task_url(task_id)
        cta_label = cta_label or "Open Task \u2192"
        is_task = True
        # subtitle is the task.title from the scheduler call
        task_title_for_card = subtitle
    elif journal_id:
        cta_url = _journal_url(journal_id)
        cta_label = cta_label or "Write Today\u2019s Journal \u2192"

    logger.info(
        "[send_reminder_email] Building email for %s | task_id=%s | journal_id=%s | is_task=%s | cta_url=%s",
        to_email, task_id, journal_id, is_task, cta_url
    )

    html_body = _build_reminder_html(
        title,
        subtitle,
        body_text,
        icon,
        cta_url=cta_url,
        cta_label=cta_label,
        task_title=task_title_for_card,
        is_task=is_task,
    )
    plain_cta = f"\n\nOpen in Memo: {cta_url}" if cta_url else ""
    text_body = f"{title}\n{subtitle}\n\n{body_text}{plain_cta}\n\n\u2014 Built by Sadguru ({_GITHUB_URL}) \u00b7 {_BRAND}"

    try:
        _send_via_gmail(to_email, subject, text_body, html_body, log_label="Reminder Email")
    except HttpError as error:
        logger.error("Gmail API error sending reminder: %s", error)
    except Exception as e:
        logger.error("Failed to send reminder email: %s", e)