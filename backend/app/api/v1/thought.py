from typing import List
from sqlalchemy import case, func, select
from models import models
from core.dependencies import db_session
from core.config import oauth2_scheme
from schema.UserAndThought import UserOut
from schema.UserAndThought import (
    ThoughtCreate,
    ThoughtUpdate,
    ThoughtSummary,
    ThoughtDetail,
    BulkDeleteThoughts,
)
from fastapi import HTTPException, Path, Depends, APIRouter
from services.auth import get_current_user

CONTENT_PREVIEW_MAX = 120
TITLE_PREVIEW_MAX = 60


def _preview_column(column, max_len: int):
    trimmed = func.trim(column)
    return case(
        (
            func.length(trimmed) > max_len,
            func.concat(func.left(trimmed, max_len), "…"),
        ),
        else_=trimmed,
    )


def _summary_query(user: UserOut):
    query = (
        select(
            models.Thought.id,
            _preview_column(models.Thought.title, TITLE_PREVIEW_MAX).label("title"),
            _preview_column(models.Thought.content, CONTENT_PREVIEW_MAX).label(
                "content_preview"
            ),
            models.Thought.user_id,
            models.Thought.created_at,
            models.Thought.updated_at,
        )
        .order_by(models.Thought.id.desc())
    )
    if user.role != "admin":
        query = query.where(models.Thought.user_id == user.id)
    return query


async def get_thoughts(db: db_session, user: UserOut) -> List[ThoughtSummary]:
    result = await db.execute(_summary_query(user))
    rows = result.all()
    return [
        ThoughtSummary(
            id=row.id,
            title=row.title or "",
            content_preview=row.content_preview or "",
            user_id=row.user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


async def get_thought(db: db_session, id: int, user: UserOut) -> ThoughtDetail:
    query = select(models.Thought).where(models.Thought.id == id)
    if user.role != "admin":
        query = query.where(models.Thought.user_id == user.id)

    result = await db.execute(query)
    thought = result.scalar_one_or_none()
    if not thought:
        raise HTTPException(
            status_code=404,
            detail=f"Thought with id {id} not found or you do not have permission to view it.",
        )
    return thought


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


async def update_thought(db: db_session, id: int, thought_data: ThoughtUpdate, user: UserOut):
    result = await db.execute(
        select(models.Thought).where(models.Thought.id == id, models.Thought.user_id == user.id)
    )
    db_thought = result.scalar_one_or_none()
    
    if not db_thought:
        raise HTTPException(
            status_code=404,
            detail=f"Thought with id {id} not found or you do not have permission to update it."
        )
    
    update_fields = thought_data.dict(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(db_thought, field, value)
    
    await db.commit()
    await db.refresh(db_thought)

    return {"message": "Thought updated successfully", "thought": db_thought}


async def bulk_delete_thoughts(db: db_session, ids: List[int], user: UserOut):
    result = await db.execute(
        select(models.Thought).where(
            models.Thought.id.in_(ids),
            models.Thought.user_id == user.id
        )
    )
    thoughts = result.scalars().all()
    for thought in thoughts:
        await db.delete(thought)
    await db.commit()
    return {"message": f"{len(thoughts)} thought(s) deleted successfully."}

app = APIRouter()

@app.get("/thoughts", response_model=List[ThoughtSummary])
async def read_thoughts(db: db_session, token: str = Depends(oauth2_scheme)):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    return await get_thoughts(db, user)


@app.get("/thoughts/{id}", response_model=ThoughtDetail)
async def read_thought(
    db: db_session,
    id: int = Path(..., description="ID of the thought to retrieve"),
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    return await get_thought(db, id, user)


@app.post("/thoughts", response_model=ThoughtDetail)
async def add_thought(
    thought: ThoughtCreate,
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
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
    id: int,
    thought: ThoughtUpdate,
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    return await update_thought(db, id, thought, user)


@app.post("/thoughts/bulk-delete")
async def bulk_delete(
    payload: BulkDeleteThoughts,
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    return await bulk_delete_thoughts(db, payload.ids, user)
