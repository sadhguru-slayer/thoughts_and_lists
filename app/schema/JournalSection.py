from typing import List, Optional
from pydantic import BaseModel
from .FieldValue import FieldValueCreate

class JournalSectionCreate(BaseModel):
    name: str
    template_id: Optional[int] = None
    reusable: bool = True
    field_values: List[FieldValueCreate] = []