from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime
class ThoughtBase(BaseModel):
    id: int
    title: str
    content: str
    user_id: int
    class Config:
        orm_mode = True
        from_attributes = True

class ThoughtCreate(BaseModel):
    title: str
    content: str

class ThoughtUpdate(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None


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

class OTPRequest(BaseModel):
    email: str

class OTPVerify(BaseModel):
    email: str
    otp: str

class ResetPassword(BaseModel):
    email: str
    otp: str
    new_password: str