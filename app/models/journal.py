from datetime import datetime
from sqlalchemy import Enum as SQLEnum

from sqlalchemy.sql import func
from sqlalchemy import (
    String, Integer, DateTime, Boolean,
    ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


from enum import Enum

class FieldType(str, Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"


class Journal(Base):
    __tablename__ = 'journals'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="journals")
    journal_sections: Mapped[list["JournalSection"]] = relationship(
        "JournalSection", back_populates="journal", cascade="all, delete-orphan"
    )

class TemplateStatus(str, Enum):
    ACTIVE = "active"        # currently in use
    TERMINATED = "terminated"  # no longer used

class SectionTemplate(Base):
    __tablename__ = 'section_templates'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    status: Mapped[TemplateStatus] = mapped_column(
        SQLEnum(TemplateStatus, name="template_status"),
        default=TemplateStatus.ACTIVE,
        nullable=False
    )

    user: Mapped["User"] = relationship(
    "User",
    back_populates="section_templates",
    foreign_keys=[user_id]  # ✅ ADD THIS
    )
    section_fields: Mapped[list["SectionField"]] = relationship(
        "SectionField",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="SectionField.order"  # ordering applied
    )
    journal_sections: Mapped[list["JournalSection"]] = relationship(
        "JournalSection", back_populates="template"
    )


class SectionField(Base):
    __tablename__ = "section_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    template_id: Mapped[int] = mapped_column(
        ForeignKey("section_templates.id"),
        nullable=False
    )

    label: Mapped[str] = mapped_column(String, nullable=False)

    # ✅ FIXED: proper Enum
    field_type: Mapped[FieldType] = mapped_column(
        SQLEnum(FieldType, name="field_type"),
        nullable=False
    )

    placeholder: Mapped[str] = mapped_column(String, nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False)

    order: Mapped[int] = mapped_column(Integer, default=0)

    template: Mapped["SectionTemplate"] = relationship(
        "SectionTemplate",
        back_populates="section_fields"
    )

    field_values: Mapped[list["FieldValue"]] = relationship(
        "FieldValue",
        back_populates="field"
    )

class JournalSection(Base):
    __tablename__ = "journal_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    journal_id: Mapped[int] = mapped_column(
        ForeignKey("journals.id"), nullable=False
    )

    # optional reference (for tracking origin)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("section_templates.id"), nullable=True
    )

    # ✅ SNAPSHOT
    name: Mapped[str] = mapped_column(String, nullable=False)

    journal: Mapped["Journal"] = relationship(
        "Journal", back_populates="journal_sections"
    )

    template: Mapped["SectionTemplate"] = relationship(
        "SectionTemplate"
    )

    field_values: Mapped[list["FieldValue"]] = relationship(
        "FieldValue",
        back_populates="section",
        cascade="all, delete-orphan"
    )

class FieldValue(Base):
    __tablename__ = "field_values"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    section_id: Mapped[int] = mapped_column(
        ForeignKey("journal_sections.id"),
        nullable=False
    )

    field_id: Mapped[int | None] = mapped_column(
        ForeignKey("section_fields.id"),
        nullable=True
    )

    value: Mapped[str] = mapped_column(Text, nullable=True)

    # ✅ Snapshot fields (correct design)
    label: Mapped[str] = mapped_column(String, nullable=False)
    field_type: Mapped[str] = mapped_column(String, nullable=False)

    section: Mapped["JournalSection"] = relationship(
        "JournalSection",
        back_populates="field_values"
    )

    field: Mapped["SectionField"] = relationship("SectionField")