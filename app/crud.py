from sqlalchemy.orm import Session
from typing import Annotated
from sqlalchemy import select
from . import models
from app.dependencies import db_session
from app.schema import ThoughtCreate,ThoughtBase
from fastapi import Form

async def get_thoughts(db: db_session):
    result = await db.execute(select(models.Thought))
    thoughts = result.scalars().all()
    return thoughts  # returns empty list automatically if no results

async def create_thought(db: db_session, post: ThoughtCreate):
    print(post)
    new_thought = models.Thought(title=post.title, content=post.content)
    db.add(new_thought)
    await db.commit()
    await db.refresh(new_thought)
    return new_thought

async def delete_thought(db: db_session, id: int):
    result = await db.execute(select(models.Thought).filter(models.Thought.id == id))
    thought = result.scalar_one_or_none()
    if thought:
        await db.delete(thought)
        await db.commit()
        return {"message": f"Thought with id {id} deleted successfully."}
    else:
        return {"error": f"Thought with id {id} not found."}