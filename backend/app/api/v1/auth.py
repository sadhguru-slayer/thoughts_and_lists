from fastapi import APIRouter,HTTPException,Depends,Form,Header,BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from core.dependencies import db_session
from core.config import ACCESS_TOKEN_EXPIRE_MINUTES,REFRESH_TOKEN_EXPIRE_MINUTES, oauth2_scheme
from datetime import timedelta,datetime
from schema.UserAndThought import UserCreate,UserOut,Role,OTPRequest,OTPVerify, ResetPassword, RegisterPasswordRequest
from services.auth import create_access_token,create_refresh_token,verify_token,verify_password,get_user_email,get_password_hashed,get_current_admin_user
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


@app.post('/request-register-otp')
async def request_register_otp(data: OTPRequest, background_tasks: BackgroundTasks, db: db_session):
    user_email = await get_user_email(db, data.email)
    if user_email:
        raise HTTPException(status_code=400, detail=f"User with the email: {data.email} already exists")

    otp_code = f"{random.randint(100000, 999999)}"
    await OTPService.save(
        OTPPurpose.REGISTER,
        data.email,
        otp_code
    )

    background_tasks.add_task(send_otp_email, data.email, otp_code, OTPPurpose.REGISTER)
    return {"message": "Registration OTP sent"}

@app.post('/verify-register-otp')
async def verify_register_otp(data: OTPVerify, db: db_session):
    user_email = await get_user_email(db, data.email)
    if user_email:
        raise HTTPException(status_code=400, detail=f"User with the email: {data.email} already exists")

    stored = await OTPService.get(
        OTPPurpose.REGISTER,
        data.email
    )

    if not stored:
        raise HTTPException(400, "OTP Expired or Not Requested")
    
    if stored != data.otp:
        raise HTTPException(401, "Invalid OTP")
    
    await OTPService.delete(
        OTPPurpose.REGISTER,
        data.email
    )

    register_token = await create_access_token(
        data={"sub": data.email, "scope": "register_verify"},
        expires_delta=timedelta(minutes=10)
    )

    return {"register_token": register_token}

@app.post('/register')
async def register(
    payload: RegisterPasswordRequest,
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    token_payload = await verify_token(token)

    if token_payload.get("scope") != "register_verify":
        raise HTTPException(status_code=403, detail="Invalid token scope")

    email = token_payload.get("sub")
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")

    user_exists = await get_user_email(db, email)
    if user_exists:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_password = get_password_hashed(payload.password)
    username = await generate_unique_username(db, email)

    new_user = User(
        username=username,
        hashed_password=hashed_password,
        role=payload.role or UserRole.USER,
        email=email
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(data={"sub": new_user.email}, expires_delta=access_expires, role=new_user.role)
    refresh_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = await create_refresh_token(data={"sub": new_user.email}, expires_delta=refresh_expires)

    return {
        "message": "User registered successfully", 
        "user": UserOut.from_orm(new_user),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

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
async def delete_user(
    email: str,
    db: db_session,
    admin: User = Depends(get_current_admin_user),
):
    user = await get_user_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found with mail {email}")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account")
    await db.delete(user)
    await db.commit()

    return {"message": f"Deleted user with Email:{email}"}

from schema.enums import OTPPurpose

from pydantic import BaseModel
class ResetPasswordRequest(BaseModel):
    new_password: str

@app.post('/reset-password')
async def reset_password(
    payload: ResetPasswordRequest,
    token: str = Depends(oauth2_scheme),
    db: db_session = None
):
    new_password = payload.new_password
    ...
    payload = await verify_token(token)

    if payload.get("scope") != "password_reset":
        raise HTTPException(status_code=403, detail="Invalid token scope")

    email = payload.get("sub")
    user = await get_user_email(db, email)

    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.hashed_password = get_password_hashed(new_password)
    await db.commit()

    return {"message": "Password reset successful"}

from services.otp import OTPService

@app.post('/request-password-reset')
async def request_password_reset(data: OTPRequest, background_tasks: BackgroundTasks, db: db_session):
    user = await get_user_email(db, data.email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    otp_code = f"{random.randint(100000, 999999)}"
    await OTPService.save(
        OTPPurpose.PASSWORD_RESET,
        user.email,
        otp_code
    )

    background_tasks.add_task(send_otp_email, user.email, otp_code,OTPPurpose.PASSWORD_RESET)

    return {"message": "Password reset OTP sent"}

@app.post('/verify-reset-otp')
async def verify_reset_otp(data: OTPVerify, db: db_session):
    user = await get_user_email(db, data.email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    stored =await OTPService.get(
        OTPPurpose.PASSWORD_RESET,
        user.email
    )

    if not stored:
        raise HTTPException(400,"OTP Expired or Not Requested")
    
    if stored != data.otp:
        raise HTTPException(401, "Invalid OTP")
    await OTPService.delete(
        OTPPurpose.PASSWORD_RESET,
        user.email
    )

    # 🔥 Issue RESET TOKEN (NOT ACCESS TOKEN)
    reset_token = await create_access_token(
        data={"sub": user.email, "scope": "password_reset"},
        expires_delta=timedelta(minutes=10),
        role=user.role
    )

    return {"reset_token": reset_token}


@app.post('/request-otp')
async def request_otp(data: OTPRequest, background_tasks: BackgroundTasks, db: db_session):
    user = await get_user_email(db, data.email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found, please register")
    
    # Generate 6 digit OTP
    otp_code = f"{random.randint(100000, 999999)}"
    
    await OTPService.save(
        OTPPurpose.LOGIN,
        user.email,
        otp_code
    )
    
    background_tasks.add_task(send_otp_email, user.email, otp_code,OTPPurpose.LOGIN)
    return {"message": "OTP sent to your email successfully"}

@app.post('/verify-otp')
async def verify_otp(data: OTPVerify, db: db_session):
    user = await get_user_email(db, data.email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    stored = await OTPService.get(
        OTPPurpose.LOGIN,
        user.email
    )

    if not stored:
        raise HTTPException(status_code=400, detail="OTP Expired or Not Requested")
        
    if stored != data.otp:
        raise HTTPException(status_code=401, detail="Invalid OTP")
    await OTPService.delete(
        OTPPurpose.LOGIN,
        user.email
    )
        
    access_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(data={"sub": user.email}, expires_delta=access_expires, role=user.role)
    refresh_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = await create_refresh_token(data={"sub": user.email}, expires_delta=refresh_expires)
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
