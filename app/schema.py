from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime
class ThoughtBase(BaseModel):
    id:int
    title:str
    content:str

class ThoughtCreate(BaseModel):
    title:str
    content:str


class Role(str,Enum):
    USER = 'user'
    ADMIN = 'admin'

class UserCreate(BaseModel):
    email:str
    password:str
    role: Role

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime
    class Config:
        orm_mode = True
        from_attributes = True