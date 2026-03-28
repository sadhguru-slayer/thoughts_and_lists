from api.v1 import thought,auth
from fastapi import FastAPI, Depends, HTTPException,Path,Form
from sqlalchemy.orm import Session
from models import models
from database import SessionLocal, engine, Base
from contextlib import asynccontextmanager
from database import init_db
from typing import Annotated
from schema.UserAndThought import ThoughtCreate,ThoughtBase
from core.dependencies import db_session
from api.v1.auth import app as authRouter
from api.v1.thought import app as thoughtRouter
from api.v1.journal import app as journalRouter


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

app.include_router(
    journalRouter,
    prefix = "/api/v1",
    tags=["Journal"]
)