# services/email.py

import base64
import logging
import os
from email.message import EmailMessage
from email.utils import make_msgid
from core.config import SMTP_USERNAME, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from schema.enums import OTPPurpose

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Brand constants
# ---------------------------------------------------------------------------
_BRAND           = "Memo"
_BRAND_COLOR     = "#6c63ff"
_BRAND_GRADIENT  = "linear-gradient(135deg, #6c63ff 0%, #5a52d5 100%)"
_GITHUB_URL      = "https://github.com/sadhguru-slayer"
_FOOTER_NOTE     = 'Built with ♥ by <a href="{url}" style="color:#6c63ff;text-decoration:none;" target="_blank">Sadguru</a>'.format(url=_GITHUB_URL)

# Logo file lives next to this module (copied from frontend/public)
_LOGO_PATH = os.path.join(os.path.dirname(__file__), "memo_logo.jpeg")

def _load_logo_bytes() -> bytes | None:
    try:
        with open(_LOGO_PATH, "rb") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning("Memo logo not found at %s — emails will render without it", _LOGO_PATH)
        return None


# ---------------------------------------------------------------------------
# Shared HTML header/footer snippets
# ---------------------------------------------------------------------------

def _html_header(icon: str, title: str, subtitle: str = "", logo_cid: str = "") -> str:
    logo_tag = ""
    if logo_cid:
        logo_tag = f"""
      <div style="text-align:center;margin-bottom:12px;">
        <img src="cid:{logo_cid}"
             alt="{_BRAND} logo"
             width="96" height="96"
             style="width:96px;height:96px;object-fit:cover;border-radius:16px;
                    background:#fff;padding:6px;display:inline-block;"/>
      </div>"""

    sub_row = ""
    if subtitle:
        sub_row = f'<div class="header-sub">{subtitle}</div>'

    return f"""
      <div class="header">
        {logo_tag}
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

def generate_email_content(otp_code: str, purpose: OTPPurpose, logo_cid: str = ""):
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

    header = _html_header(icon, title, logo_cid=logo_cid)
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

def _build_reminder_html(title: str, subtitle: str, body_text: str, icon: str = "🔔", logo_cid: str = "") -> str:
    header = _html_header(icon, title, subtitle=subtitle, logo_cid=logo_cid)
    footer = _html_footer(
        f"You're receiving this because reminders are enabled in your {_BRAND} settings.<br/>"
        "You can update your preferences anytime from the app."
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
  .message-box{{background:linear-gradient(135deg,#f7f5ff,#eeeeff);border-left:4px solid {_BRAND_COLOR};border-radius:10px;padding:18px 20px;font-size:15px;color:#333;line-height:1.7}}
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
    .message-box{{font-size:14px;padding:14px 16px}}
  }}
  @media (prefers-color-scheme:dark){{
    body,.wrap{{background:#0d0d14!important}}
    .card{{background:#1a1a2e!important;box-shadow:0 8px 40px rgba(0,0,0,.5)!important}}
    .body{{background:#1a1a2e!important}}
    .message-box{{background:linear-gradient(135deg,#16213e,#1a1a38)!important;border-left-color:#6c63ff!important;color:#ccc!important}}
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
          <div class="message-box">{body_text}</div>
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
    creds = Credentials(
        token=None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        client_id=GMAIL_CLIENT_ID,
        client_secret=GMAIL_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("gmail", "v1", credentials=creds)


def _send_via_gmail(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    logo_bytes: bytes | None = None,
    log_label: str = "Email",
):
    """Build a multipart/related message with an optional inline logo attachment."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage

    # Build multipart/related so the CID image is scoped to the HTML part
    msg_root = MIMEMultipart("related")
    msg_root["Subject"] = subject
    msg_root["From"]    = SMTP_USERNAME
    msg_root["To"]      = to_email

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(text_body, "plain", "utf-8"))
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg_root.attach(alt)

    if logo_bytes:
        img = MIMEImage(logo_bytes, _subtype="jpeg")
        img.add_header("Content-ID", "<memo_logo>")
        img.add_header("Content-Disposition", "inline", filename="memo_logo.jpeg")
        msg_root.attach(img)

    service = _get_gmail_service()
    encoded = base64.urlsafe_b64encode(msg_root.as_bytes()).decode()
    result  = service.users().messages().send(userId="me", body={"raw": encoded}).execute()
    logger.info("%s sent to %s | ID: %s", log_label, to_email, result.get("id"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

from core.config import ENVIRONMENT


def send_otp_email(to_email: str, otp_code: str, purpose: OTPPurpose):
    if ENVIRONMENT != "production":
        logger.debug("[DEV] OTP for %s: %s", purpose, otp_code)
        return

    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET or not GMAIL_REFRESH_TOKEN:
        logger.error("Gmail credentials not set in .env")
        return

    logo_bytes = _load_logo_bytes()
    logo_cid   = "memo_logo" if logo_bytes else ""
    subject, text_body, html_body = generate_email_content(otp_code, purpose, logo_cid=logo_cid)

    try:
        _send_via_gmail(to_email, subject, text_body, html_body, logo_bytes=logo_bytes, log_label="OTP Email")
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
    icon: str = "🔔",
):
    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET or not GMAIL_REFRESH_TOKEN:
        logger.error("Gmail credentials not set in .env")
        return

    logo_bytes = _load_logo_bytes()
    logo_cid   = "memo_logo" if logo_bytes else ""
    html_body  = _build_reminder_html(title, subtitle, body_text, icon, logo_cid=logo_cid)
    text_body  = f"{title}\n{subtitle}\n\n{body_text}\n\n— Built by Sadguru ({_GITHUB_URL}) · {_BRAND}"

    try:
        _send_via_gmail(to_email, subject, text_body, html_body, logo_bytes=logo_bytes, log_label="Reminder Email")
    except HttpError as error:
        logger.error("Gmail API error sending reminder: %s", error)
    except Exception as e:
        logger.error("Failed to send reminder email: %s", e)