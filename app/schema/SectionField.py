from pydantic import BaseModel
from typing import Optional


class SectionFieldCreate(BaseModel):
    label: str
    field_type: str  # ideally FieldType enum
    placeholder: Optional[str] = None
    required: bool = False
    order: int = 0