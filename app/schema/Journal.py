from datetime import datetime
from typing import Optional,List

from pydantic import BaseModel, Field
from .JournalSection import JournalSectionCreate


class JournalBase(BaseModel):
    date: datetime = Field(..., description="Date of the journal entry")
    content: Optional[str] = Field(None, description="Main journal content")


class JournalCreate(JournalBase):
    sections: Optional[List[JournalSectionCreate]] = None


class JournalResponse(JournalBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True