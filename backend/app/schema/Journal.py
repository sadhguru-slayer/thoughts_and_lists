from datetime import datetime
from typing import Optional,List

from pydantic import BaseModel, Field
from .JournalSection import JournalSectionCreate


class JournalBase(BaseModel):
    date: datetime = Field(..., description="Date of the journal entry")
    content: Optional[str] = Field(None, description="Main journal content")

from pydantic import model_validator

class JournalCreate(JournalBase):
    template_id: Optional[int] = None
    sections: Optional[List[JournalSectionCreate]] = None

    @model_validator(mode="after")
    def validate_input(self):
        if self.template_id and self.sections:
            # allowed → filled template
            return self
        if not self.template_id and not self.sections and not self.content:
            raise ValueError("Journal must have content, template_id, or sections")

        return self


class JournalResponse(JournalBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True