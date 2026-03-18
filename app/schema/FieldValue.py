from typing import Optional
from pydantic import BaseModel


class FieldValueCreate(BaseModel):
    label: str
    field_type: str
    value: Optional[str] = None

    field_id: Optional[int] = None