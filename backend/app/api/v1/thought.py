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
    BulkThoughtOrderUpdate,
)
from fastapi import HTTPException, Path, Depends, APIRouter
from uuid import UUID
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
            models.Thought.uuid,
            _preview_column(models.Thought.title, TITLE_PREVIEW_MAX).label("title"),
            _preview_column(models.Thought.content, CONTENT_PREVIEW_MAX).label(
                "content_preview"
            ),
            models.Thought.user_id,
            models.Thought.created_at,
            models.Thought.updated_at,
            models.Thought.is_pinned,
            models.Thought.pinned_at,
            models.Thought.pinned_order,
            models.Thought.is_starred,
        )
        .order_by(models.Thought.id.desc())
    )
    if user.role != "admin":
        query = query.where(models.Thought.user_id == user.id)
    return query


from math import ceil
from fastapi import HTTPException, Path, Depends, APIRouter, Query

from sqlalchemy import or_

async def get_thoughts(
    db: db_session,
    user: UserOut,
    search: str | None = None,
    page: int = 1,
    per_page: int = 20
):
    count_query = select(func.count(models.Thought.id))
    if user.role != "admin":
        count_query = count_query.where(models.Thought.user_id == user.id)
    
    if search:
        count_query = count_query.where(
            or_(
                models.Thought.title.ilike(f"%{search}%"),
                models.Thought.content.ilike(f"%{search}%")
            )
        )

    total = (await db.scalar(count_query)) or 0

    query = _summary_query(user)
    if search:
        query = query.where(
            or_(
                models.Thought.title.ilike(f"%{search}%"),
                models.Thought.content.ilike(f"%{search}%")
            )
        )
    
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    rows = result.all()
    
    items = [
        ThoughtSummary(
            uuid=row.uuid,
            title=row.title or "",
            content_preview=row.content_preview or "",
            user_id=row.user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            is_pinned=row.is_pinned,
            pinned_at=row.pinned_at,
            pinned_order=row.pinned_order,
            is_starred=row.is_starred,
        )
        for row in rows
    ]
    total_pages = ceil(total / per_page) if per_page else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }


async def get_thought(db: db_session, thought_uuid: UUID, user: UserOut) -> ThoughtDetail:
    query = select(models.Thought).where(models.Thought.uuid == thought_uuid)
    if user.role != "admin":
        query = query.where(models.Thought.user_id == user.id)

    result = await db.execute(query)
    thought = result.scalar_one_or_none()
    if not thought:
        raise HTTPException(
            status_code=404,
            detail=f"Thought with uuid {thought_uuid} not found or you do not have permission to view it.",
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

async def delete_thought(db: db_session, thought_uuid: UUID, user: UserOut):
    result = await db.execute(
        select(models.Thought).where(models.Thought.uuid == thought_uuid, models.Thought.user_id == user.id)
    )
    thought = result.scalar_one_or_none()
    if not thought:
        raise HTTPException(
            status_code=404,
            detail=f"Thought with uuid {thought_uuid} not found or you do not have permission to delete it."
        )
    
    await db.delete(thought)
    await db.commit()
    return {"message": f"Thought with uuid {thought_uuid} deleted successfully."}


async def update_thought(db: db_session, thought_uuid: UUID, thought_data: ThoughtUpdate, user: UserOut):
    result = await db.execute(
        select(models.Thought).where(models.Thought.uuid == thought_uuid, models.Thought.user_id == user.id)
    )
    db_thought = result.scalar_one_or_none()
    
    if not db_thought:
        raise HTTPException(
            status_code=404,
            detail=f"Thought with uuid {thought_uuid} not found or you do not have permission to update it."
        )
    
    from datetime import datetime, timezone
    update_fields = thought_data.dict(exclude_unset=True)
    for field, value in update_fields.items():
        if field == "is_pinned":
            if value is True and not db_thought.is_pinned:
                db_thought.pinned_at = datetime.now(timezone.utc)
            elif value is False:
                db_thought.pinned_at = None
                db_thought.pinned_order = None
        setattr(db_thought, field, value)
    
    await db.commit()
    await db.refresh(db_thought)

    return {"message": "Thought updated successfully", "thought": db_thought}


async def bulk_delete_thoughts(db: db_session, uuids: List[UUID], user: UserOut):
    result = await db.execute(
        select(models.Thought).where(
            models.Thought.uuid.in_(uuids),
            models.Thought.user_id == user.id
        )
    )
    thoughts = result.scalars().all()
    for thought in thoughts:
        await db.delete(thought)
    await db.commit()
    return {"message": f"{len(thoughts)} thought(s) deleted successfully."}

app = APIRouter()

@app.get("/thoughts")
async def read_thoughts(
    db: db_session,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    return await get_thoughts(db, user, search=search, page=page, per_page=per_page)


@app.get("/thoughts/{thought_uuid}", response_model=ThoughtDetail)
async def read_thought(
    db: db_session,
    thought_uuid: UUID = Path(..., description="UUID of the thought to retrieve"),
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    return await get_thought(db, thought_uuid, user)


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


@app.delete("/thoughts/{thought_uuid}")
async def remove_thought(
    db: db_session,
    thought_uuid: UUID = Path(..., description="UUID of the thought to delete"),
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    return await delete_thought(db, thought_uuid, user)


@app.patch("/thoughts/{thought_uuid}")
async def update_thoughts(
    thought_uuid: UUID,
    thought: ThoughtUpdate,
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    return await update_thought(db, thought_uuid, thought, user)


@app.post("/thoughts/bulk-delete")
async def bulk_delete(
    payload: BulkDeleteThoughts,
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    return await bulk_delete_thoughts(db, payload.uuids, user)

@app.post("/thoughts/update-order")
async def update_thought_orders(
    payload: BulkThoughtOrderUpdate,
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    
    uuids = [item.uuid for item in payload.orders]
    result = await db.execute(
        select(models.Thought).where(
            models.Thought.uuid.in_(uuids),
            models.Thought.user_id == user.id
        )
    )
    thoughts = result.scalars().all()
    thought_map = {t.uuid: t for t in thoughts}
    
    for item in payload.orders:
        if item.uuid in thought_map:
            thought_map[item.uuid].pinned_order = item.pinned_order
            
    await db.commit()
    return {"message": "Thought orders updated successfully"}
