from fastapi import FastAPI, Depends, HTTPException,Path,Form
from sqlalchemy.orm import Session
from . import models, crud
from .database import SessionLocal, engine, Base
from contextlib import asynccontextmanager
from app.database import init_db
from typing import Annotated
from app.schema import ThoughtCreate
from app.dependencies import db_session



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
    results = await crud.get_thoughts(db)
    return results

@app.post("/thoughts")
async def add_thought(
    post:ThoughtCreate,
    db: db_session
):
    return await crud.create_thought(db, post)

@app.delete("/thoughts/{id}")
async def delete_thought(db: db_session,id: int = Path(..., description="ID of the thought to delete")):
    return await crud.delete_thought(db, id)