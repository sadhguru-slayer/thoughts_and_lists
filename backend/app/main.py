from api.v1 import thought, auth
from fastapi import FastAPI
from sqlalchemy.orm import Session
from models import models
from database import SessionLocal, engine, Base
from contextlib import asynccontextmanager
from database import init_db
from typing import Annotated
from core.dependencies import db_session
from api.v1.auth import app as authRouter
from api.v1.thought import app as thoughtRouter
from api.v1.journal import app as journalRouter

# ✅ ADD THIS
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Thoughts API", lifespan=lifespan)

# ✅ ADD THIS BLOCK (CORS CONFIG)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    prefix="/api/v1",
    tags=["Journal"]
)