from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional, List

# --- Note Schemas ---

class NoteBase(BaseModel):
    title: str
    content: str

class NoteCreate(NoteBase):
    pass

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_starred: Optional[bool] = None

class NoteOut(NoteBase):
    uuid: UUID
    notebook_id: int
    user_id: int
    is_pinned: bool
    is_starred: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# --- Notebook Schemas ---

class NotebookBase(BaseModel):
    name: str
    description: Optional[str] = None

class NotebookCreate(NotebookBase):
    pass

class NotebookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class NotebookOut(NotebookBase):
    uuid: UUID
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class NotebookWithNotesOut(NotebookOut):
    notes: List[NoteOut] = []

class MoveNoteRequest(BaseModel):
    target_notebook_uuid: Optional[UUID] = None

class MoveThoughtRequest(BaseModel):
    target_notebook_uuid: UUID
