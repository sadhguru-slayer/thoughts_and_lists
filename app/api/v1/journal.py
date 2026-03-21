from sqlalchemy.orm import Session,selectinload
from typing import Annotated, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,delete
from app.models import models
from app.core.dependencies import db_session
from app.core.config import oauth2_scheme
from app.schema.UserAndThought import UserOut
from app.schema.UserAndThought import ThoughtCreate,ThoughtBase
from fastapi import Form,HTTPException, Path, Depends, APIRouter
from app.services.auth import get_current_user
from app.schema.Journal import JournalCreate
from app.schema.JournalSection import JournalSectionCreate
from app.models import journal
from enum import Enum
app = APIRouter()

@app.get("/templates", response_model=List[dict])
async def get_existing_templates(
    db: db_session,
    token:str = Depends(oauth2_scheme)
):
    # 1️⃣ Get current user
    current_user= await get_current_user(db, token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 2️⃣ Fetch templates for this user with fields (eager load)
    result = await db.execute(
        select(journal.SectionTemplate)
        .options(selectinload(journal.SectionTemplate.section_fields))
        .where(journal.SectionTemplate.user_id == current_user.id)
    )
    templates = result.scalars().all()

    # 3️⃣ Convert to JSON-friendly dict
    output = []
    for t in templates:
        output.append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            # Optional status: active/inactive
            "status": getattr(t, "status", "active"),  
            "fields": [
                {
                    "id": f.id,
                    "label": f.label,
                    "field_type": f.field_type.value if isinstance(f.field_type, Enum) else f.field_type,
                    "placeholder": f.placeholder,
                    "required": f.required,
                    "order": f.order
                } for f in t.section_fields
            ]
        })

    return output

from collections import defaultdict


@app.post("/journal")
async def create_journal(
    data: JournalCreate,
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    # 1️⃣ Authenticate user
    current_user = await get_current_user(db, token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 2️⃣ Create the journal
    new_journal = journal.Journal(
        user_id=current_user.id,
        date=data.date,
        content=data.content
    )
    db.add(new_journal)
    await db.flush()  # Get journal.id

    sections_data = data.sections or []

    # 3️⃣ Collect template_ids for all sections upfront
    template_ids = [s.template_id for s in sections_data if s.template_id]

    # 4️⃣ Fetch all template fields in one query
    template_fields_map = defaultdict(list)
    if template_ids:
        result = await db.execute(
            select(journal.SectionField).where(
                journal.SectionField.template_id.in_(template_ids)
            )
        )
        fields = result.scalars().all()
        for f in fields:
            template_fields_map[f.template_id].append(f)

    # 5️⃣ Process each section
    for section_data in sections_data:
        section = journal.JournalSection(
            journal_id=new_journal.id,
            template_id=section_data.template_id,
            name=section_data.name
        )
        db.add(section)
        await db.flush()  # Get section.id

        existing_labels = {fv.label for fv in (section_data.field_values or [])}

        # CASE A: Existing template
        if section_data.template_id:
            template_fields = template_fields_map[section_data.template_id]
            for field in template_fields:
                if field.label not in existing_labels:
                    db.add(journal.FieldValue(
                        section_id=section.id,
                        field_id=field.id,
                        label=field.label,
                        field_type=field.field_type.value,
                        value=None
                    ))

        # CASE B: Create reusable template
        elif getattr(section_data, "reusable", False):
            new_template = journal.SectionTemplate(
                user_id=current_user.id,
                name=section_data.name,
                description=f"Created from journal {new_journal.id}"
            )
            db.add(new_template)
            await db.flush()

            template_fields = []
            for order, fv in enumerate(section_data.field_values or []):
                tf = journal.SectionField(
                    template_id=new_template.id,
                    label=fv.label,
                    field_type=fv.field_type,
                    order=order
                )
                db.add(tf)
                template_fields.append(tf)

            await db.flush()  # ✅ single flush for all new fields

            # Assign field_ids back to field values
            for fv, tf in zip(section_data.field_values or [], template_fields):
                fv.field_id = tf.id

            section.template_id = new_template.id

        # Insert all user-provided field values
        for fv in section_data.field_values or []:
            db.add(journal.FieldValue(
                section_id=section.id,
                field_id=fv.field_id,
                label=fv.label,
                field_type=fv.field_type,
                value=fv.value
            ))

    # 6️⃣ Commit transaction
    await db.commit()

    # 7️⃣ Refresh and return
    await db.refresh(new_journal)
    return new_journal

@app.delete("/journal/{journal_id}")
async def delete_journal(
    db: db_session,
    journal_id: int = Path(..., description="ID of the journal to delete"),
    token: str = Depends(oauth2_scheme)
):
    # Get current user
    current_user = await get_current_user(db, token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Ensure journal exists & belongs to user
    result = await db.execute(
        select(journal.Journal)
        .where(journal.Journal.id == journal_id)
        .where(journal.Journal.user_id == current_user.id)
    )
    existing_journal = result.scalar_one_or_none()
    if not existing_journal:
        raise HTTPException(status_code=404, detail="Journal not found")

    # Delete all FieldValues of the journal's sections
    await db.execute(
        delete(journal.FieldValue).where(
            journal.FieldValue.section_id.in_(
                select(journal.JournalSection.id)
                .where(journal.JournalSection.journal_id == journal_id)
            )
        )
    )

    # Delete all sections of the journal
    await db.execute(
        delete(journal.JournalSection).where(
            journal.JournalSection.journal_id == journal_id
        )
    )

    # Finally, delete the journal
    await db.execute(
        delete(journal.Journal).where(journal.Journal.id == journal_id)
    )

    # Commit the changes
    await db.commit()

    return  {"message":"Deleted successfully"}