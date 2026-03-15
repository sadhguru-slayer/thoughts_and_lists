from datetime import datetime,timedelta,timezone
from app.core.config import pwd_context,oauth2_scheme
from sqlalchemy import select
from app.models import User,UserRole
from datetime import datetime
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES,SECRET_KEY,ALGORITHM
from fastapi import Depends,HTTPException,status
import jwt

def get_password_hashed(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(pwd:str,h_pwd:str)-> bool:
    return pwd_context.verify(pwd,h_pwd)

async def get_user_username(db,username: str):
    data = await db.execute(select(User).where(User.username == username))
    user = data.scalar_one_or_none()
    return user

async def get_user_email(db,email: str):
    data = await db.execute(select(User).where(User.email == email))
    user = data.scalar_one_or_none()
    return user

async def create_access_token(data:dict, expires_delta:timedelta = None, role:str=None):
    to_encode = data.copy()
    if role:
        to_encode['role']=role
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    access_token = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return access_token

async def create_refresh_token(data:dict,expires_delta:timedelta=None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    refresh_token = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return refresh_token

async def verify_token(token:str):
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401,detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401,detail="Invalid token")