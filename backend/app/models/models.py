from datetime import datetime
from enum import Enum
from sqlalchemy.sql import func
from sqlalchemy import String, Integer, DateTime, Boolean, Enum as SQLEnum, ForeignKey, Text, Index, Time, Date
from sqlalchemy.orm import Mapped, mapped_column
from database import Base
from sqlalchemy.orm import relationship
# from .journal import Journal
from datetime import time, datetime

class Thought(Base):
    __tablename__ = "thoughts"
    __table_args__ = (
        Index("ix_thoughts_user_id_id", "user_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="thoughts")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now()
    )

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    hashed_password: Mapped[str] = mapped_column(String, nullable=False)

    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role"),
        default=UserRole.USER
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )

    thoughts: Mapped[list["Thought"]] = relationship(
        "Thought",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    journals: Mapped[list["Journal"]] = relationship(
        "Journal",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # ✅ FIXED: missing relationship
    section_templates: Mapped[list["SectionTemplate"]] = relationship(
        "SectionTemplate",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys='SectionTemplate.user_id'  # <-- explicitly tell SQLAlchemy which FK
    )

    default_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("section_templates.id"),
        nullable=True
    )
    tasks = relationship(
        "Task",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    otp_code: Mapped[str | None] = mapped_column(String, nullable=True)
    otp_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Reminders Settings
    timezone: Mapped[str] = mapped_column(String, default="Asia/Kolkata", server_default="Asia/Kolkata")
    journal_reminder_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    journal_reminder_time: Mapped[time] = mapped_column(
        Time,
        default=time(22, 0),
        nullable=False,
    )
    last_journal_reminder_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)