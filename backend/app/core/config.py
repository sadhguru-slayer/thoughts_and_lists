import os
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

load_dotenv()

SECRET_KEY ='3RA27JmF18ikTwH19dsdfb772t3YDzSl4LKEzDNzcCq2dBsqY='
ALGORITHM ='HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("EMAIL")
SMTP_PASSWORD = os.getenv("APP_PASSWORD")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/token')
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")