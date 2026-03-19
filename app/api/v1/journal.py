from sqlalchemy.orm import Session,selectinload
from typing import Annotated, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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

@app.post("/journal")
async def create_journal(
    data: JournalCreate,
    db: db_session,
    token:str = Depends(oauth2_scheme)
):
    print(data)
    current_user = await get_current_user(db,token)
    if not current_user:
        raise HTTPException(status_code = 404, detail = "Invalid token")
    
    new_journal = journal.Journal(
        user_id=current_user.id,
        date=data.date,
        content=data.content
    )
    db.add(new_journal)
    await db.flush()
    
    for section_data in data.sections or []:
        section = journal.JournalSection(
            journal_id=new_journal.id,
            template_id=section_data.template_id,
            name=section_data.name
        )
        db.add(section)
        await db.flush()

        if section_data.template_id:
            result = await db.execute(
                select(journal.SectionField).where(
                    journal.SectionField.template_id == section_data.template_id
                )
            )
            template_fields = result.scalars().all()
            template_field_map = {f.label: f for f in template_fields}

            for label, field in template_field_map.items():
                if not any(fv.label == label for fv in section_data.field_values):
                    field_value = journal.FieldValue(
                        section_id=section.id,
                        field_id=field.id,
                        label=field.label,
                        field_type=field.field_type.value,
                        value=None
                    )
                    db.add(field_value)

        elif section_data.reusable:
            new_template = journal.SectionTemplate(
                user_id=current_user.id,
                name=section_data.name,
                description=f"Created from journal {new_journal.id}"
            )
            db.add(new_template)
            await db.flush()

            for order, fv in enumerate(section_data.field_values):
                template_field = journal.SectionField(
                    template_id=new_template.id,
                    label=fv.label,
                    field_type=fv.field_type,
                    order=order
                )
                db.add(template_field)
                await db.flush()
                fv.field_id = template_field.id
            section.template_id = new_template.id

        for fv in section_data.field_values:
            field_value = journal.FieldValue(
                section_id=section.id,
                field_id=fv.field_id,
                label=fv.label,
                field_type=fv.field_type,
                value=fv.value
            )
            db.add(field_value)
    await db.commit()
    await db.refresh(new_journal)
    return new_journal