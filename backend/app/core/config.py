from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

SECRET_KEY ='3RA27JmF18ikTwH19dsdfb772t3YDzSl4LKEzDNzcCq2dBsqY='
ALGORITHM ='HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week expiration for refresh token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/token')
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")