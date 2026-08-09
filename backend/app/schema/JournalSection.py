from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from .FieldValue import FieldValueCreate

class JournalSectionCreate(BaseModel):
    name: str
    template_uuid: Optional[UUID] = None
    reusable: bool = True
    field_values: List[FieldValueCreate] = []