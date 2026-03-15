from fastapi import APIRouter,HTTPException,Depends,Form,Header
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from app.core.dependencies import db_session
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES,REFRESH_TOKEN_EXPIRE_MINUTES
from datetime import timedelta,datetime
from app.schema import UserCreate,UserOut

app = APIRouter()

@app.post('/token')
async def token(db:db_session,form_data:Annotated[OAuth2PasswordRequestForm,Depends()]):
    pass

@app.post('/register')
async def register(db:db_session,form_data:Annotated[UserCreate,Form()]):
    pass

@app.post('/refresh-token')
async def refresh_token(refresh_token:Annotated[str,Header(...,title="Refresh Token")],db:db_session):
    pass