from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import Uuid
import uuid6
from database import Base

class Notebook(Base):
    __tablename__ = "notebooks"
    __table_args__ = (
        Index("ix_notebooks_user_id_id", "user_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[str] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False, unique=True, default=uuid6.uuid7)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    user: Mapped["User"] = relationship("User", back_populates="notebooks")
    notes: Mapped[list["Note"]] = relationship("Note", back_populates="notebook", cascade="all, delete-orphan")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now()
    )

class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        Index("ix_notes_notebook_id_id", "notebook_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[str] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False, unique=True, default=uuid6.uuid7)
    title: Mapped[str] = mapped_column(String, index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    notebook_id: Mapped[int] = mapped_column(Integer, ForeignKey("notebooks.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    is_pinned: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    is_starred: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    
    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="notes")
    user: Mapped["User"] = relationship("User", back_populates="notes")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now()
    )
