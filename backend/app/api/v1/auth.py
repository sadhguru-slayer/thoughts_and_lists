from fastapi import APIRouter,HTTPException,Depends,Form,Header,BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from core.dependencies import db_session
from core.config import ACCESS_TOKEN_EXPIRE_MINUTES,REFRESH_TOKEN_EXPIRE_MINUTES
from datetime import timedelta,datetime
from schema.UserAndThought import UserCreate,UserOut,Role,OTPRequest,OTPVerify
from services.auth import create_access_token,create_refresh_token,verify_token,verify_password,get_user_email,get_password_hashed
from models.models import User,UserRole

from services.email import send_otp_email
import re
import secrets
import random
from sqlalchemy import select

async def generate_unique_username(db, email: str):
    base = email.split("@")[0].lower()
    base = re.sub(r"[^a-z0-9_]", "", base)

    username = base

    while True:
        result = await db.execute(select(User).where(User.username == username))
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            return username

        suffix = secrets.token_hex(2)
        username = f"{base}_{suffix}"

app = APIRouter()

@app.post('/token')
async def token(db:db_session,form_data:Annotated[OAuth2PasswordRequestForm,Depends()]):
    user = await get_user_email(db,form_data.username)
    if not user:
        raise HTTPException(status_code=400,detail="User not exist, please register")
    if not verify_password(form_data.password,user.hashed_password):
        raise HTTPException(status_code=401,detail="Invalid Credentials")
    access_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(data={"sub":user.email},expires_delta=access_expires,role=user.role)
    refresh_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = await create_refresh_token(data={"sub":user.email},expires_delta=refresh_expires)
    return {"access_token":access_token,"refresh_token":refresh_token,"token_type":"bearer"}


@app.post('/register')
async def register(form_data: UserCreate, db: db_session):
    user_email = await get_user_email(db, form_data.email)
    if user_email:
        raise HTTPException(status_code=400, detail=f"User with the email: {form_data.email} already exists")

    hashed_password = get_password_hashed(form_data.password)
    username = await generate_unique_username(db, form_data.email)

    new_user = User(
        username=username,
        hashed_password=hashed_password,
        role=UserRole.USER,
        email=form_data.email
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {"message": "User registered successfully", "user": UserOut.from_orm(new_user)}

@app.post('/refresh-token')
async def refresh_token(refresh_token:Annotated[str,Header(...,title="Refresh Token")],db:db_session):
    try:
        payload = await verify_token(refresh_token)
        email = payload.get('sub')
        if not email:
            raise HTTPException(status_code=401,detail="Invalid token")
        user = await get_user_email(db,email)
        if not user:
            raise HTTPException(status_code=400,detail="User not exist, please register")
        access_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = await create_access_token(data={"sub":user.email},expires_delta=access_expires,role=user.role)
        refresh_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
        refresh_token = await create_refresh_token(data={"sub":user.email},expires_delta=refresh_expires)
        return {"access_token":access_token,"refresh_token":refresh_token,"token_type":"bearer"}
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    

# Admin actions
@app.delete('/delete-user')
async def delete_user(email:str,db:db_session):
    user = await get_user_email(db,email)
    if not user:
        raise HTTPException(status_code = 404, detail = f"User not found with mail {email}")
    await db.delete(user)
    await db.commit()

    return {"message":f"Deleted user with Email:{email}"}

@app.post('/request-otp')
async def request_otp(data: OTPRequest, background_tasks: BackgroundTasks, db: db_session):
    user = await get_user_email(db, data.email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found, please register")
    
    # Generate 6 digit OTP
    otp_code = f"{random.randint(100000, 999999)}"
    
    # Set expiry to 10 minutes from now
    user.otp_code = otp_code
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    
    await db.commit()
    
    background_tasks.add_task(send_otp_email, user.email, otp_code)
    return {"message": "OTP sent to your email successfully"}

@app.post('/verify-otp')
async def verify_otp(data: OTPVerify, db: db_session):
    user = await get_user_email(db, data.email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
        
    if not user.otp_code or not user.otp_expiry:
        raise HTTPException(status_code=400, detail="OTP not requested")
        
    if user.otp_code != data.otp:
        raise HTTPException(status_code=401, detail="Invalid OTP")
        
    # Check expiry but ensure naive/aware datetime handling works. 
    # Use timezone-naive utcnow() if model doesn't specify tz mapping issues. Wait, SQLAlchemy func.now() was used, so let's check with tzinfo.
    now = datetime.utcnow()
    # If the db is timezone-aware and we get an offset-aware datetime out, we need to compare it correctly, 
    # but let's assume naive or strip tz info.
    # A safer way to avoid "can't compare offset-naive and offset-aware datetimes":
    otp_expiry = user.otp_expiry.replace(tzinfo=None) if user.otp_expiry.tzinfo else user.otp_expiry
    
    if now > otp_expiry:
        raise HTTPException(status_code=401, detail="OTP has expired")
        
    # Clear OTP after successful verify
    user.otp_code = None
    user.otp_expiry = None
    await db.commit()
    
    access_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(data={"sub": user.email}, expires_delta=access_expires, role=user.role)
    refresh_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = await create_refresh_token(data={"sub": user.email}, expires_delta=refresh_expires)
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
