from .api.v1 import thought
from fastapi import FastAPI, Depends, HTTPException,Path,Form
from sqlalchemy.orm import Session
from . import models
from .database import SessionLocal, engine, Base
from contextlib import asynccontextmanager
from app.database import init_db
from typing import Annotated
from app.schema import ThoughtCreate,ThoughtBase
from app.core.dependencies import db_session



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

@app.get("/thoughts")
async def read_thoughts(db: db_session):
    results = await thought.get_thoughts(db)
    return results

@app.post("/thoughts")
async def add_thought(
    thought:ThoughtCreate,
    db: db_session
):
    return await thought.create_thought(db, thought)

@app.delete("/thoughts/{id}")
async def delete_thought(db: db_session,id: int = Path(..., description="ID of the thought to delete")):
    return await thought.delete_thought(db, id)

@app.patch("/thoughts/{id}")
async def update_thoughts(db:db_session,thought:ThoughtBase):
    return await thought.update_thought(db,thought)
    