import base64
from email.message import EmailMessage
from core.config import SMTP_USERNAME, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def send_otp_email(to_email: str, otp_code: str):
    print(f"------- Started send_otp_email for: {to_email} via Gmail API", flush=True)
    
    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET or not GMAIL_REFRESH_TOKEN:
        print("------- Gmail API Credentials not set properly in .env", flush=True)
        return

    msg = EmailMessage()
    msg['Subject'] = 'Your OTP Code'
    msg['From'] = SMTP_USERNAME
    msg['To'] = to_email
    
    msg.set_content(f"""\
Hi,

Your OTP code for logging in is: {otp_code}

This code is valid for 10 minutes. Please do not share this code with anyone.

Thanks,
Thoughts Team""")

    try:
        print("------- Constructing Gmail API credentials...", flush=True)
        # Construct the Credentials from the environment variables
        creds = Credentials(
            token=None,  # Will automatically use the refresh_token to fetch a fresh token
            refresh_token=GMAIL_REFRESH_TOKEN,
            client_id=GMAIL_CLIENT_ID,
            client_secret=GMAIL_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token"
        )
        
        print("------- Building Gmail service (v1)...", flush=True)
        service = build('gmail', 'v1', credentials=creds)
        
        print("------- Encoding email message...", flush=True)
        encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        print("------- Hitting users.messages.send API...", flush=True)
        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
        
        print(f"------- Email sent successfully via Gmail HTTP API! Message Id: {sent_message.get('id')}", flush=True)

    except HttpError as error:
        print(f"------- An HttpError occurred via Gmail API: {error}", flush=True)
    except Exception as e:
        print(f"------- Failed to send email via API: {e}", flush=True)
