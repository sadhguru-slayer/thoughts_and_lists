from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class FieldValueCreate(BaseModel):
    label: str
    field_type: str
    value: Optional[str] = None

    field_uuid: Optional[UUID] = None