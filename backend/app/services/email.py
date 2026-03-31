# services/email.py

import base64
from email.message import EmailMessage
from core.config import SMTP_USERNAME, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from schema.enums import OTPPurpose


def generate_email_content(otp_code: str, purpose: OTPPurpose):
    if purpose == OTPPurpose.LOGIN:
        subject = "Your Login OTP Code"
        title = "Login Verification"
        subtitle = "Use the OTP below to continue logging in."
    elif purpose == OTPPurpose.PASSWORD_RESET:
        subject = "Reset Your Password"
        title = "Password Reset Request"
        subtitle = "Use the OTP below to reset your password."
    else:
        subject = "Your OTP Code"
        title = "Verification Code"
        subtitle = "Use the OTP below."

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">

<style>
    * {{
        box-sizing: border-box;
    }}

    body {{
        margin:0;
        padding:0;
        background-color:#f4f6f8;
        font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
    }}

    table {{
        border-spacing:0;
    }}

    .wrapper {{
        width:100%;
        table-layout:fixed;
        background-color:#f4f6f8;
        padding:20px 12px;
    }}

    .main {{
        max-width:420px;
        width:100%;
        background:#ffffff;
        border-radius:14px;
        padding:32px 24px;
        text-align:left;
    }}

    .brand {{
        font-size:16px;
        font-weight:600;
        color:#111;
        letter-spacing:0.3px;
    }}

    .title {{
        font-size:22px;
        font-weight:600;
        margin-top:18px;
        color:#111;
    }}

    .subtitle {{
        font-size:14px;
        color:#666;
        margin-top:8px;
        line-height:1.5;
    }}

    .otp-container {{
        text-align:center;
        margin:28px 0;
    }}

    .otp-box {{
        display:inline-block;
        padding:14px 22px;
        font-size:26px;
        letter-spacing:6px;
        font-weight:600;
        border-radius:10px;
        background:#f1f3f5;
        border:1px solid #e0e0e0;
        color:#111;
    }}

    .info {{
        font-size:13px;
        color:#777;
        text-align:center;
        line-height:1.6;
    }}

    .footer {{
        margin-top:28px;
        padding-top:16px;
        border-top:1px solid #eee;
        font-size:12px;
        color:#999;
        text-align:center;
    }}

    /* Mobile */
    @media screen and (max-width:480px) {{
        .main {{
            padding:24px 18px;
        }}

        .otp-box {{
            font-size:22px;
            letter-spacing:4px;
        }}
    }}

    /* Dark Mode */
    @media (prefers-color-scheme: dark) {{
        body, .wrapper {{
            background-color:#0e0e0e !important;
        }}

        .main {{
            background:#1a1a1a !important;
        }}

        .brand, .title {{
            color:#ffffff !important;
        }}

        .subtitle {{
            color:#bbbbbb !important;
        }}

        .otp-box {{
            background:#2a2a2a !important;
            border:1px solid #3a3a3a !important;
            color:#fff !important;
        }}

        .info {{
            color:#aaaaaa !important;
        }}

        .footer {{
            border-top:1px solid #333 !important;
            color:#777 !important;
        }}
    }}
</style>
</head>

<body>
<center class="wrapper">
    <table width="100%" role="presentation">
        <tr>
            <td align="center">

                <!-- Card -->
                <table class="main" role="presentation">
                    <tr>
                        <td>

                            <div class="brand">ThoughtsHub</div>

                            <div class="title">{title}</div>
                            <div class="subtitle">{subtitle}</div>

                            <div class="otp-container">
                                <div class="otp-box">{otp_code}</div>
                            </div>

                            <div class="info">
                                This code is valid for 10 minutes.<br/>
                                Do not share this code with anyone.
                            </div>

                            <div class="footer">
                                If you didn’t request this, you can safely ignore this email.
                            </div>

                        </td>
                    </tr>
                </table>

            </td>
        </tr>
    </table>
</center>
</body>
</html>
"""

    text_body = f"""
{title}

{subtitle}

Your OTP: {otp_code}

This code is valid for 10 minutes.
"""

    return subject, text_body, html_body
from core.config import ENVIRONMENT

def send_otp_email(to_email: str, otp_code: str, purpose: OTPPurpose):
    print(f"------- Sending {purpose} OTP email to: {to_email}", flush=True)

    if ENVIRONMENT != "production":
        print(f"--------- OTP FOR {purpose} : {otp_code} ------------")
        return
    
    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET or not GMAIL_REFRESH_TOKEN:
        print("------- Gmail API Credentials not set properly in .env", flush=True)
        return

    subject, text_body, html_body = generate_email_content(otp_code, purpose)
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SMTP_USERNAME
    msg['To'] = to_email

    # ✅ Plain fallback
    msg.set_content(text_body)

    # ✅ HTML version
    msg.add_alternative(html_body, subtype='html')

    try:
        creds = Credentials(
            token=None,
            refresh_token=GMAIL_REFRESH_TOKEN,
            client_id=GMAIL_CLIENT_ID,
            client_secret=GMAIL_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token"
        )

        service = build('gmail', 'v1', credentials=creds)

        encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        sent_message = service.users().messages().send(
            userId="me",
            body=create_message
        ).execute()

        print(f"------- Email sent! ID: {sent_message.get('id')}", flush=True)

    except HttpError as error:
        print(f"------- Gmail API error: {error}", flush=True)
    except Exception as e:
        print(f"------- Failed to send email: {e}", flush=True)