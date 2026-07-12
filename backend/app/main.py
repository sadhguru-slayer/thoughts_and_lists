from contextlib import asynccontextmanager

from api.v1 import thought, auth
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from database import init_db
from api.v1.auth import app as authRouter
from api.v1.thought import app as thoughtRouter
from api.v1.journal import app as journalRouter
from api.v1.tasks import app as taskRouter
from api.v1.dashboard import app as dashboardRouter
load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
FRONTEND_URL_2 = os.getenv("FRONTEND_URL_2", "http://localhost:3000")
IS_DEVELOPMENT = ENVIRONMENT == "development"

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield




app = FastAPI(
    title="Thoughts API",
    lifespan=lifespan,
    docs_url="/docs" if IS_DEVELOPMENT else None,
    redoc_url="/redoc" if IS_DEVELOPMENT else None,
    openapi_url="/openapi.json" if IS_DEVELOPMENT else None,
)

from core.redis import redis_client

@app.on_event("startup")
async def startup():
    await redis_client.ping()

# Configure CORS based on environment
if ENVIRONMENT == "production":
    origins = [FRONTEND_URL, FRONTEND_URL_2]
else:  # development
    origins = [
        FRONTEND_URL,
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

app.include_router(
    taskRouter,
    prefix="/api/v1",
    tags=["Task"]
)

app.include_router(
    dashboardRouter,
    prefix="/api/v1",
    tags=["Dashboard"]
)