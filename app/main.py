from app.api.v1 import thought,auth
from fastapi import FastAPI, Depends, HTTPException,Path,Form
from sqlalchemy.orm import Session
from app.models import models
from app.database import SessionLocal, engine, Base
from contextlib import asynccontextmanager
from app.database import init_db
from typing import Annotated
from app.schema import ThoughtCreate,ThoughtBase
from app.core.dependencies import db_session
from app.api.v1.auth import app as authRouter
from app.api.v1.thought import app as thoughtRouter


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Thoughts API", lifespan=lifespan)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.include_router(
    authRouter,
    prefix="/api/v1/auth",
    tags=["Auth"]
)

app.include_router(
    thoughtRouter,
    prefix="/api/v1",
    tags=["Thought"]
)

