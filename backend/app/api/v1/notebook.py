from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy import select
from typing import List
from uuid import UUID

from core.dependencies import db_session
from core.config import oauth2_scheme
from models.models import User, Thought
from models.notebook import Notebook, Note
from schema.Notebook import (
    NotebookCreate, NotebookUpdate, NotebookOut, NotebookWithNotesOut,
    NoteCreate, NoteUpdate, NoteOut, MoveNoteRequest, MoveThoughtRequest
)
from services.auth import get_current_user

router = APIRouter()

# --- Notebook Endpoints ---

@router.post("/notebooks", response_model=NotebookOut, status_code=status.HTTP_201_CREATED)
async def create_notebook(
    notebook: NotebookCreate,
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    db_notebook = Notebook(**notebook.model_dump(), user_id=user.id)
    db.add(db_notebook)
    await db.commit()
    await db.refresh(db_notebook)
    return db_notebook

@router.get("/notebooks", response_model=List[NotebookWithNotesOut])
async def get_notebooks(
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Notebook)
        .options(selectinload(Notebook.notes))
        .where(Notebook.user_id == user.id)
        .order_by(Notebook.id.desc())
    )
    notebooks = result.scalars().all()
    return notebooks

@router.get("/notebooks/{uuid}", response_model=NotebookWithNotesOut)
async def get_notebook(
    db: db_session,
    uuid: UUID = Path(...),
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    result = await db.execute(select(Notebook).where(Notebook.uuid == str(uuid), Notebook.user_id == user.id))
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
        
    # We need to eagerly load notes or fetch them, 
    # but since relationship might be lazy, let's just fetch notes if needed.
    # Actually, SQLAlchemy with async doesn't support lazy loading. 
    # We should fetch notes explicitly or use joinedload.
    from sqlalchemy.orm import selectinload
    result_with_notes = await db.execute(
        select(Notebook).options(selectinload(Notebook.notes)).where(Notebook.uuid == str(uuid), Notebook.user_id == user.id)
    )
    notebook_with_notes = result_with_notes.scalar_one_or_none()

    return notebook_with_notes

@router.put("/notebooks/{uuid}", response_model=NotebookOut)
async def update_notebook(
    notebook_update: NotebookUpdate,
    db: db_session,
    uuid: UUID = Path(...),
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    result = await db.execute(select(Notebook).where(Notebook.uuid == str(uuid), Notebook.user_id == user.id))
    db_notebook = result.scalar_one_or_none()
    if not db_notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    
    update_data = notebook_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_notebook, key, value)
        
    await db.commit()
    await db.refresh(db_notebook)
    return db_notebook

@router.delete("/notebooks/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook(
    db: db_session,
    uuid: UUID = Path(...),
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    result = await db.execute(select(Notebook).where(Notebook.uuid == str(uuid), Notebook.user_id == user.id))
    db_notebook = result.scalar_one_or_none()
    if not db_notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    
    await db.delete(db_notebook)
    await db.commit()
    return

# --- Note Endpoints ---

@router.post("/notebooks/{notebook_uuid}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    note: NoteCreate,
    db: db_session,
    notebook_uuid: UUID = Path(...),
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    result = await db.execute(select(Notebook).where(Notebook.uuid == str(notebook_uuid), Notebook.user_id == user.id))
    db_notebook = result.scalar_one_or_none()
    if not db_notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    db_note = Note(**note.model_dump(), notebook_id=db_notebook.id, user_id=user.id)
    db.add(db_note)
    await db.commit()
    await db.refresh(db_note)
    return db_note

@router.get("/notes/{uuid}", response_model=NoteOut)
async def get_note(
    db: db_session,
    uuid: UUID = Path(...),
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    result = await db.execute(select(Note).where(Note.uuid == str(uuid), Note.user_id == user.id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@router.put("/notes/{uuid}", response_model=NoteOut)
async def update_note(
    note_update: NoteUpdate,
    db: db_session,
    uuid: UUID = Path(...),
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    result = await db.execute(select(Note).where(Note.uuid == str(uuid), Note.user_id == user.id))
    db_note = result.scalar_one_or_none()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    update_data = note_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_note, key, value)
        
    await db.commit()
    await db.refresh(db_note)
    return db_note

@router.delete("/notes/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    db: db_session,
    uuid: UUID = Path(...),
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    result = await db.execute(select(Note).where(Note.uuid == str(uuid), Note.user_id == user.id))
    db_note = result.scalar_one_or_none()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    await db.delete(db_note)
    await db.commit()
    return

@router.post("/notes/{uuid}/move")
async def move_note(
    payload: MoveNoteRequest,
    db: db_session,
    uuid: UUID = Path(...),
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    result = await db.execute(select(Note).where(Note.uuid == str(uuid), Note.user_id == user.id))
    db_note = result.scalar_one_or_none()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")

    # If target_notebook_uuid is None, move note to Quick Notes (Thought)
    if not payload.target_notebook_uuid:
        new_thought = Thought(
            title=db_note.title,
            content=db_note.content,
            user_id=user.id
        )
        db.add(new_thought)
        await db.delete(db_note)
        await db.commit()
        await db.refresh(new_thought)
        return {"message": "Moved to Quick Notes", "type": "thought", "uuid": str(new_thought.uuid)}

    # Move to another Notebook
    target_res = await db.execute(
        select(Notebook).where(Notebook.uuid == str(payload.target_notebook_uuid), Notebook.user_id == user.id)
    )
    target_notebook = target_res.scalar_one_or_none()
    if not target_notebook:
        raise HTTPException(status_code=404, detail="Target notebook not found")

    db_note.notebook_id = target_notebook.id
    await db.commit()
    await db.refresh(db_note)
    return {"message": "Note moved to target notebook", "type": "note", "uuid": str(db_note.uuid), "notebook_uuid": str(target_notebook.uuid)}

