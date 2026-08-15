# services/email.py

import base64
import logging
import os
import pathlib
import datetime
from uuid import UUID
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
_BRAND_COLOR     = "#18181b"  # Zinc 900
_GITHUB_URL      = "https://github.com/sadhguru-slayer"
_FOOTER_NOTE     = 'Built with ♥ by <a href="{url}" class="footer-link" style="color:#18181b;text-decoration:none;font-weight:600;" target="_blank">Sadguru</a>'.format(url=_GITHUB_URL)

# ---------------------------------------------------------------------------
# CSS Styling Constants (Unified Zinc Aesthetic)
# ---------------------------------------------------------------------------
_EMAIL_STYLE = f"""
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%}}
  .wrap{{width:100%;background:#f4f4f5;padding:48px 16px}}
  .card{{max-width:520px;margin:0 auto;background:#ffffff;border:1px solid #e4e4e7;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px 0 rgba(0,0,0,0.05),0 1px 2px 0 rgba(0,0,0,0.06)}}
  .body{{padding:40px 32px 32px 32px}}
  .subtitle{{font-size:14px;color:#71717a;line-height:1.5;margin-bottom:24px}}
  .otp-wrap{{margin:0 0 24px}}
  .otp-label{{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#a1a1aa;margin-bottom:8px}}
  .otp-box{{display:inline-block;padding:16px 24px;font-size:32px;font-weight:700;letter-spacing:8px;font-family:SFMono-Regular,Consolas,"Liberation Mono",Menlo,monospace;background:#fafafa;border:1px solid #e4e4e7;border-radius:10px;color:#09090b}}
  .note{{font-size:13px;color:#52525b;line-height:1.5;background:#f4f4f5;border-radius:8px;padding:12px 16px}}
  
  /* Content boxes for Reminders (Task / Journal / Generic) */
  .content-box{{background:#fafafa;border:1px solid #e4e4e7;border-left:3px solid #09090b;border-radius:8px;padding:20px;margin-bottom:20px;text-align:left}}
  .task-title{{font-size:16px;font-weight:700;color:#09090b;text-decoration:none;line-height:1.35;display:block;word-break:break-word}}
  .task-desc{{margin:10px 0 0;font-size:14px;color:#52525b;line-height:1.6}}
  .cta-btn-wrap{{margin-top:18px}}
  .cta-btn{{display:inline-block;padding:10px 20px;background:#09090b;color:#ffffff;font-size:13px;font-weight:600;border-radius:8px;text-decoration:none;letter-spacing:.2px;transition:background-color 0.15s ease}}
  .cta-btn-center{{display:inline-block;padding:12px 24px;background:#09090b;color:#ffffff;font-size:13px;font-weight:600;border-radius:8px;text-decoration:none;letter-spacing:.2px;transition:background-color 0.15s ease}}
  
  .divider{{border:none;border-top:1px solid #e4e4e7;margin:28px 0}}
  .footer{{padding:0;text-align:center}}
  .footer p{{font-size:12px;color:#71717a;line-height:1.6}}
  .footer a{{color:#09090b;text-decoration:none;font-weight:600}}
  .badge{{display:inline-block;margin-top:12px;font-size:11px;color:#a1a1aa;letter-spacing:.3px}}

  @media only screen and (max-width:480px){{
    .wrap{{padding:24px 10px}}
    .body{{padding:28px 20px 24px 20px}}
    .otp-box{{font-size:26px;letter-spacing:6px;padding:14px 20px}}
    .header-title{{font-size:18px!important}}
  }}
  @media (prefers-color-scheme:dark){{
    body,.wrap{{background:#09090b!important}}
    .card{{background:#09090b!important;border-color:#27272a!important;box-shadow:none!important}}
    .header-title{{color:#f4f4f5!important}}
    .header-pre{{color:#a1a1aa!important}}
    .subtitle{{color:#a1a1aa!important}}
    .otp-box{{background:#18181b!important;border-color:#27272a!important;color:#f4f4f5!important}}
    .note{{background:#18181b!important;border-color:#27272a!important;color:#a1a1aa!important}}
    .content-box{{background:#18181b!important;border-color:#27272a!important;border-left-color:#f4f4f5!important;color:#f4f4f5!important}}
    .task-title{{color:#f4f4f5!important}}
    .task-desc{{color:#a1a1aa!important}}
    .cta-btn,.cta-btn-center{{background:#f4f4f5!important;color:#09090b!important}}
    .divider{{border-color:#27272a!important}}
    .footer p{{color:#71717a!important}}
    .footer a{{color:#f4f4f5!important}}
    .badge{{color:#71717a!important}}
  }}
"""

# ---------------------------------------------------------------------------
# Frontend deep-link URL builders
# ---------------------------------------------------------------------------

def _task_url(task_id: str | UUID) -> str:
    """Return the shareable frontend URL that opens a specific task."""
    base = (FRONTEND_URL or "https://memo.sadguruchenu.in").rstrip("/")
    return f"{base}/tasks?task={task_id}"


def _journal_url(journal_id: str | UUID) -> str:
    """Return the shareable frontend URL that opens a specific journal entry."""
    base = (FRONTEND_URL or "https://memo.sadguruchenu.in").rstrip("/")
    return f"{base}/journals/{journal_id}"

# ---------------------------------------------------------------------------
# Shared HTML header/footer snippets
# ---------------------------------------------------------------------------

def _html_header(icon: str, title: str, subtitle: str = "", category: str = "NOTIFICATION") -> str:
    sub_row = ""
    if subtitle:
        sub_row = f'<p class="subtitle" style="font-size:14px;color:#71717a;line-height:1.5;margin:8px 0 0 0;">{subtitle}</p>'

    return f"""
      <div class="header" style="margin-bottom:24px;text-align:left;">
        <div class="header-pre" style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#71717a;margin-bottom:8px;">
          <span class="header-icon" style="margin-right:4px;">{icon}</span>{_BRAND} · {category}
        </div>
        <h1 class="header-title" style="font-size:22px;font-weight:800;color:#09090b;margin:0;line-height:1.25;letter-spacing:-0.5px;">{title}</h1>
        {sub_row}
      </div>"""


def _html_footer(extra_note: str = "") -> str:
    note_html = ""
    if extra_note:
        note_html = f'<p style="font-size:12px;color:#71717a;line-height:1.6;margin-bottom:16px;">{extra_note}</p>'
    return f"""
          <hr class="divider" style="border:none;border-top:1px solid #e4e4e7;margin:28px 0;"/>
          <div class="footer" style="text-align:center;">
            {note_html}
            <div class="badge" style="display:inline-block;margin-top:12px;font-size:11px;color:#a1a1aa;letter-spacing:.3px;">{_FOOTER_NOTE}</div>
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
        category = "SECURITY"
    elif purpose == OTPPurpose.PASSWORD_RESET:
        subject  = f"Reset your {_BRAND} password"
        title    = "Password Reset"
        subtitle = "Use the code below to reset your password. It expires in 10 minutes."
        icon     = "🔑"
        category = "SECURITY"
    else:
        subject  = f"Your {_BRAND} OTP Code"
        title    = "Verification Code"
        subtitle = "Use the code below to continue."
        icon     = "✅"
        category = "SECURITY"

    header = _html_header(icon, title, subtitle=subtitle, category=category)
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
{_EMAIL_STYLE}
</style>
</head>
<body>
<div class="wrap">
  <table width="100%" role="presentation" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <div class="card">
        <div class="body">
          {header}
          <div class="otp-wrap" style="text-align:center;">
            <div class="otp-label">Your one-time code</div>
            <div class="otp-box">{otp_code}</div>
          </div>
          <div class="note" style="text-align:center;">
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

    text_body = f"""{_BRAND} · {title}

{subtitle}

Your OTP: {otp_code}

This code expires in 10 minutes. Do not share it with anyone.

— Built by Sadguru ({_GITHUB_URL})"""
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
    header = _html_header(icon, title, subtitle="" if is_task else subtitle, category="REMINDER")
    footer = _html_footer(
        f"You're receiving this because reminders are enabled in your {_BRAND} settings.<br/>"
        "You can update your preferences anytime from the app."
    )

    # ── Content Box Builder ───────────────────────────────────────────────
    title_html = ""
    if is_task and task_title:
        if cta_url:
            title_html = (
                f'<a href="{cta_url}" target="_blank" class="task-title" '
                f'style="font-size:16px;font-weight:700;color:#09090b;text-decoration:none;'
                f'line-height:1.35;display:block;word-break:break-word;margin-bottom:8px;">'
                f'\U0001f4cc {task_title}</a>'
            )
        else:
            title_html = (
                f'<span class="task-title" style="font-size:16px;font-weight:700;color:#09090b;line-height:1.35;'
                f'display:block;word-break:break-word;margin-bottom:8px;">\U0001f4cc {task_title}</span>'
            )

    desc_html = ""
    if body_text:
        desc_html = (
            f'<p class="task-desc" style="font-size:14px;color:#52525b;line-height:1.6;margin:0;">'
            f'{body_text}</p>'
        )

    view_btn = ""
    if cta_url and cta_label:
        view_btn = (
            f'<div class="cta-btn-wrap" style="margin-top:16px;">'
            f'<a href="{cta_url}" target="_blank" class="cta-btn" '
            f'style="display:inline-block;padding:10px 20px;background:#09090b;'
            f'color:#ffffff;font-size:13px;font-weight:600;border-radius:8px;text-decoration:none;'
            f'letter-spacing:.2px;">'
            f'{cta_label}</a></div>'
        )

    content_html = f"""
      <div class="content-box" style="background:#fafafa;
           border:1px solid #e4e4e7;border-left:3px solid #09090b;border-radius:8px;
           padding:20px;margin-bottom:20px;text-align:left;">
        {title_html}
        {desc_html}
        {view_btn}
      </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="color-scheme" content="light dark"/>
<title>{title}</title>
<style>
{_EMAIL_STYLE}
</style>
</head>
<body>
<div class="wrap">
  <table width="100%" role="presentation" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <div class="card">
        <div class="body">
          {header}
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
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_label = log_label.lower().replace(" ", "_")
    filename = f"{ts}_{safe_label}.html"
    filepath = _DEV_PREVIEW_DIR / filename
    filepath.write_text(html_body, encoding="utf-8")
    return str(filepath)


def _send_via_gmail(to_email: str, subject: str, text_body: str, html_body: str, log_label: str = "Email"):
    # logger.info("==================== EMAIL SEND DEBUG ====================")
    # logger.info("ENVIRONMENT Mode: %s", ENVIRONMENT)
    # logger.info("Subject: %s | To: %s | Label: %s", subject, to_email, log_label)
    # logger.info("Generated HTML Content:\n%s", html_body)
    # logger.info("==========================================================")

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
    task_id: str | UUID | None = None,
    journal_id: str | UUID | None = None,
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
        task_title_for_card = subtitle
    elif "task" in title.lower():
        # Fallback: if task_id wasn't passed by scheduler, still treat it as a task email
        is_task = True
        task_title_for_card = subtitle

    elif journal_id:
        cta_url = _journal_url(journal_id)
        cta_label = cta_label or "Open Journal \u2192"
    elif "journal" in title.lower():
        # Fallback for daily journal reminder (creates a new journal)
        base = (FRONTEND_URL or "https://memo.sadguruchenu.in").rstrip("/")
        cta_url = f"{base}/journals/write"
        cta_label = cta_label or "Write Today\u2019s Journal \u2192"

    # logger.info(
    #     "[send_reminder_email] Building email for %s | task_id=%s | journal_id=%s | is_task=%s | cta_url=%s",
    #     to_email, task_id, journal_id, is_task, cta_url
    # )

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