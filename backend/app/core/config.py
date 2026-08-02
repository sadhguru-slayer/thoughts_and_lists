import os
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

load_dotenv()

SECRET_KEY ='3RA27JmF18ikTwH19dsdfb772t3YDzSl4LKEzDNzcCq2dBsqY='
ALGORITHM ='HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("EMAIL")
SMTP_PASSWORD = os.getenv("APP_PASSWORD")

GMAIL_CLIENT_ID = os.getenv("CLIENT_ID") or os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("CLIENT_SECRET") or os.getenv("CLIENT_SECRETE") or os.getenv("GMAIL_CLIENT_SECRET")
GMAIL_REFRESH_TOKEN = os.getenv("REFRESH_TOKEN") or os.getenv("GMAIL_REFRESH_TOKEN")
GMAIL_ACCESS_TOKEN = os.getenv("ACCESS_TOKEN") or os.getenv("GMAIL_ACCESS_TOKEN")
GMAIL_PROJECT_ID = os.getenv("PROJECT_ID") or os.getenv("GMAIL_PROJECT_ID")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://memo.sadguruchenu.in")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/token')
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")