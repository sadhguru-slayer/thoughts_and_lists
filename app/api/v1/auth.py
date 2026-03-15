from fastapi import APIRouter,HTTPException,Depends,Form,Header
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from app.core.dependencies import db_session
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES,REFRESH_TOKEN_EXPIRE_MINUTES
from datetime import timedelta,datetime
from app.schema import UserCreate,UserOut,Role
from app.services.auth import create_access_token,create_refresh_token,verify_token,verify_password,get_user_email,get_password_hashed
from app.models import User,UserRole

import re
import secrets
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
