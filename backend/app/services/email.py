import smtplib
import logging
from email.message import EmailMessage
from core.config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def send_otp_email(to_email: str, otp_code: str):
    logger.info(f"------- Started send_otp_email for: {to_email}")
    
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        err_msg = "------- SMTP Credentials not set. Cannot send email. Ensure EMAIL and APP_PASSWORD are in your .env"
        logger.error(err_msg)
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
        logger.info(f"------- Attempting to connect to SMTP server: {SMTP_SERVER}:{SMTP_PORT} using IPv4")
        # Force the connection to use IPv4 to fix "Network is unreachable" error on Railway
        # Railway instances sometimes fail to route IPv6 packets correctly.
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, source_address=("0.0.0.0", 0)) as server:
            server.set_debuglevel(1) # Enable this temporarily to output verbose SMTP logs to the console
            logger.info("------- Starting TLS...")
            server.starttls()
            logger.info("------- Logging in...")
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            logger.info("------- Login successful, sending message...")
            server.send_message(msg)
            logger.info("------- Email sent successfully!")
            
    except Exception as e:
        logger.error(f"------- Failed to send email: {e}")
