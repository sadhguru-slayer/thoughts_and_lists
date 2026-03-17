from sqlalchemy.orm import Session
from typing import Annotated
from sqlalchemy import select
from app.models import models
from app.core.dependencies import db_session
from app.core.config import oauth2_scheme
from app.schema.UserAndThought import UserOut
from app.schema.UserAndThought import ThoughtCreate,ThoughtBase
from fastapi import Form,HTTPException, Path, Depends, APIRouter
from app.services.auth import get_current_user


app = APIRouter()


# @app.post('/journal')
# async def create_journal():