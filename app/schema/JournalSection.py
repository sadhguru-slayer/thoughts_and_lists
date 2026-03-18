from typing import List, Optional
from pydantic import BaseModel
from .FieldValue import FieldValueCreate

class JournalSectionCreate(BaseModel):
    name: str
    template_id: Optional[int] = None

    field_values: List[FieldValueCreate] = []