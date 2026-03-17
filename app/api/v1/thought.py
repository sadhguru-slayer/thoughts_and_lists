from sqlalchemy.orm import Session
from typing import Annotated
from sqlalchemy import select
from app.models import models
from app.core.dependencies import db_session
from app.core.config import oauth2_scheme
from app.schema import UserOut
from app.schema import ThoughtCreate,ThoughtBase
from fastapi import Form,HTTPException, Path, Depends
from app.services.auth import get_current_user

async def get_thoughts(db: db_session, user: UserOut):
    print(user)
    if user.role == "admin":
        result = await db.execute(select(models.Thought))
    else:
        result = await db.execute(
            select(models.Thought).where(models.Thought.user_id == user.id)
        )
    
    thoughts = result.scalars().all()
    return thoughts

async def create_thought(db: db_session, thought: ThoughtCreate, user: UserOut):
    new_thought = models.Thought(
        title=thought.title,
        content=thought.content,
        user_id=user.id
    )
    db.add(new_thought)
    await db.commit()
    await db.refresh(new_thought)
    return new_thought

async def delete_thought(db: db_session, id: int, user: UserOut):
    result = await db.execute(
        select(models.Thought).where(models.Thought.id == id, models.Thought.user_id == user.id)
    )
    thought = result.scalar_one_or_none()
    if not thought:
        raise HTTPException(
            status_code=404,
            detail=f"Thought with id {id} not found or you do not have permission to delete it."
        )
    
    await db.delete(thought)
    await db.commit()
    return {"message": f"Thought with id {id} deleted successfully."}


async def update_thought(db: db_session, thought_data: ThoughtBase, user: UserOut):
    result = await db.execute(
        select(models.Thought).where(models.Thought.id == thought_data.id, models.Thought.user_id == user.id)
    )
    db_thought = result.scalar_one_or_none()
    
    if not db_thought:
        raise HTTPException(
            status_code=404,
            detail=f"Thought with id {thought_data.id} not found or you do not have permission to update it."
        )
    
    update_fields = thought_data.dict(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(db_thought, field, value)
    
    await db.commit()
    await db.refresh(db_thought)

    return {"message": "Thought updated successfully", "thought": db_thought}

from fastapi import APIRouter

app = APIRouter()

@app.get("/thoughts")
async def read_thoughts(db: db_session,token:str = Depends(oauth2_scheme)):
    user = await get_current_user(db,token)
    if not user:
        raise HTTPException(status_code = 404, detail = "Invalid token")
    results = await get_thoughts(db, user)
    return results

@app.post("/thoughts")
async def add_thought(
    thought: ThoughtCreate,
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    print(user)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    return await create_thought(db, thought, user)


@app.delete("/thoughts/{id}")
async def remove_thought(
    db: db_session,
    id: int = Path(..., description="ID of the thought to delete"),
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    return await delete_thought(db, id, user)


@app.patch("/thoughts/{id}")
async def update_thoughts(
    db: db_session,
    thought: ThoughtBase,
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    return await update_thought(db, thought, user)
