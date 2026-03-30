import smtplib
import logging
from email.message import EmailMessage
from core.config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

def send_otp_email(to_email: str, otp_code: str):
    print(f"------- Started send_otp_email for: {to_email}", flush=True)
    
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        err_msg = "------- SMTP Credentials not set. Cannot send email. Ensure EMAIL and APP_PASSWORD are in your .env"
        print(err_msg, flush=True)
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
Thoughts Team
""")

    try:
        print(f"------- Attempting to connect to SMTP server: {SMTP_SERVER}:{SMTP_PORT} using IPv4", flush=True)
        # Force the connection to use IPv4 to fix "Network is unreachable" error on Railway
        # Railway instances sometimes fail to route IPv6 packets correctly.
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, source_address=("0.0.0.0", 0)) as server:
            server.set_debuglevel(1) # Enable this temporarily to output verbose SMTP logs to the console
            print("------- Starting TLS...", flush=True)
            server.starttls()
            print("------- Logging in...", flush=True)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            print("------- Login successful, sending message...", flush=True)
            server.send_message(msg)
            print("------- Email sent successfully!", flush=True)
            
    except Exception as e:
        print(f"------- Failed to send email: {e}", flush=True)
