from sqlalchemy.orm import Session
from typing import Annotated
from sqlalchemy import select
from app.models import models
from app.core.dependencies import db_session
from app.schema import ThoughtCreate,ThoughtBase
from fastapi import Form,HTTPException

async def get_thoughts(db: db_session):
    result = await db.execute(select(models.Thought))
    thoughts = result.scalars().all()
    return thoughts  # returns empty list automatically if no results

async def create_thought(db: db_session, thought: ThoughtCreate):
    print(thought)
    new_thought = models.Thought(title=thought.title, content=thought.content)
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
    
async def update_thought(db:db_session,thought:ThoughtBase):
    result = await db.execute(select(models.Thought).where(models.Thought.id == thought.id))
    db_thought = result.scalar_one_or_none()

    if not db_thought:
        raise HTTPException(status_code=404,detail="No Thought Found")
    
    update_fields = thought.dict(exclude_unset=True)

    for field, value in update_fields.items():
        setattr(db_thought,field,value)
    
    await db.commit()
    await db.refresh(db_thought)

    return {"message": "Thought updated successfully", "thought": db_thought}


