from datetime import datetime
from enum import Enum
from sqlalchemy.sql import func
from sqlalchemy import String, Integer, DateTime, Boolean, Enum as SQLEnum, ForeignKey,Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from sqlalchemy.orm import relationship

class Thought(Base):
    __tablename__ = "thoughts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="thoughts")

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    hashed_password: Mapped[str] = mapped_column(String, nullable=False)

    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole, name="user_role"), default=UserRole.USER)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


    thoughts: Mapped[list["Thought"]] = relationship("Thought", back_populates="user", cascade="all, delete-orphan")

    default_template_id: Mapped[int | None] = mapped_column(
    ForeignKey("section_templates.id"), nullable=True
    )