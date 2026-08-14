from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
from datetime import datetime, time
from uuid import UUID

class ThoughtBase(BaseModel):
    uuid: UUID
    title: str
    content: str
    user_id: int
    class Config:
        from_attributes = True


class ThoughtSummary(BaseModel):
    uuid: UUID
    title: str
    content_preview: str
    user_id: int
    created_at: datetime
    updated_at: datetime
    is_pinned: Optional[bool] = False
    pinned_at: Optional[datetime] = None
    pinned_order: Optional[int] = None
    is_starred: Optional[bool] = False

    class Config:
        from_attributes = True


class ThoughtDetail(BaseModel):
    uuid: UUID
    title: str
    content: str
    user_id: int
    created_at: datetime
    updated_at: datetime
    is_pinned: Optional[bool] = False
    pinned_at: Optional[datetime] = None
    pinned_order: Optional[int] = None
    is_starred: Optional[bool] = False

    class Config:
        from_attributes = True

class ThoughtCreate(BaseModel):
    title: str
    content: str

class ThoughtUpdate(BaseModel):
    uuid: Optional[UUID] = None
    title: Optional[str] = None
    content: Optional[str] = None
    is_pinned: Optional[bool] = None
    pinned_order: Optional[int] = None
    is_starred: Optional[bool] = None


class BulkDeleteThoughts(BaseModel):
    uuids: List[UUID]

class ThoughtOrderUpdate(BaseModel):
    uuid: UUID
    pinned_order: int

class BulkThoughtOrderUpdate(BaseModel):
    orders: List[ThoughtOrderUpdate]


class Role(str,Enum):
    USER = 'user'
    ADMIN = 'admin'

class UserCreate(BaseModel):
    email:str
    password:str
    role: Role

class UserOut(BaseModel):
    uuid: UUID
    username: str
    email: str
    role: str
    created_at: datetime
    timezone: Optional[str] = "Asia/Kolkata"
    journal_reminder_active: Optional[bool] = True
    journal_reminder_time: Optional[time] = None
    class Config:
        from_attributes = True

class UserSettingsUpdate(BaseModel):
    timezone: Optional[str] = None
    journal_reminder_active: Optional[bool] = None
    journal_reminder_time: Optional[time] = None

class OTPRequest(BaseModel):
    email: str

class OTPVerify(BaseModel):
    email: str
    otp: str

class ResetPassword(BaseModel):
    email: str
    otp: str
    new_password: str

class RegisterPasswordRequest(BaseModel):
    password: str
    role: Optional[Role] = Role.USER