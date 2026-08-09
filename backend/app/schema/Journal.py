from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field
from .JournalSection import JournalSectionCreate


class JournalBase(BaseModel):
    date: datetime = Field(..., description="Date of the journal entry")
    content: Optional[str] = Field(None, description="Main journal content")

from pydantic import model_validator

class JournalCreate(JournalBase):
    template_uuid: Optional[UUID] = None
    sections: Optional[List[JournalSectionCreate]] = None

    @model_validator(mode="after")
    def validate_input(self):
        if self.template_uuid and self.sections:
            # allowed → filled template
            return self
        if not self.template_uuid and not self.sections and not self.content:
            raise ValueError("Journal must have content, template_uuid, or sections")

        return self


class JournalResponse(JournalBase):
    uuid: UUID
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FieldValueUpdate(BaseModel):
    uuid: UUID
    value: Optional[str] = None


class JournalSectionUpdate(BaseModel):
    uuid: UUID
    name: Optional[str] = None
    field_values: List[FieldValueUpdate] = []


class JournalUpdate(BaseModel):
    date: Optional[datetime] = None
    content: Optional[str] = None
    sections: List[JournalSectionUpdate] = []