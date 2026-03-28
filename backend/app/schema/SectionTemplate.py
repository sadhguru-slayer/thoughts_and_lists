from typing import List, Optional
from pydantic import BaseModel
from .SectionField import SectionFieldCreate


class SectionTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_default: bool = False  # "use this every day"

    fields: List[SectionFieldCreate]