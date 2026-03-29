from sqlalchemy.orm import Session,selectinload
from typing import Annotated, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,delete,func
from models import models
from core.dependencies import db_session
from core.config import oauth2_scheme
from schema.UserAndThought import UserOut
from schema.UserAndThought import ThoughtCreate,ThoughtBase
from fastapi import Form,HTTPException, Path, Depends, APIRouter
from services.auth import get_current_user
from schema.Journal import JournalCreate,JournalResponse
from schema.JournalSection import JournalSectionCreate
from models import journal
from enum import Enum
app = APIRouter()

@app.get("/journals",response_model = List[JournalResponse])
async def get_journals(db:db_session,token:str = Depends(oauth2_scheme)):
    current_user = await get_current_user(db,token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(
        select(journal.Journal)
        .where(journal.Journal.user_id == current_user.id)
        .order_by(journal.Journal.date.desc())
    )
    journals = result.scalars().all()
    return journals


@app.get("/journal/analytics")
async def get_journal_analytics(
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(db, token)
    print(current_user,"----------------")
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 1️⃣ Total journals
    total_result = await db.execute(
        select(func.count(journal.Journal.id))
        .where(journal.Journal.user_id == current_user.id)
    )
    total_journals = total_result.scalar()

    # 2️⃣ Journals per day
    daily_result = await db.execute(
        select(
            func.date(journal.Journal.date),
            func.count(journal.Journal.id)
        )
        .where(journal.Journal.user_id == current_user.id)
        .group_by(func.date(journal.Journal.date))
        .order_by(func.date(journal.Journal.date))
    )

    daily_counts = [
        {"date": str(row[0]), "count": row[1]}
        for row in daily_result.all()
    ]

    return {
        "total_journals": total_journals,
        "daily_activity": daily_counts
    }


@app.get("/journal/{journal_id}")
async def get_journal_detail(
    journal_id: int,
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(db, token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(
        select(journal.Journal)
        .options(
            selectinload(journal.Journal.journal_sections)
            .selectinload(journal.JournalSection.field_values)
        )
        .where(journal.Journal.id == journal_id)
        .where(journal.Journal.user_id == current_user.id)
    )

    journal_obj = result.scalar_one_or_none()

    if not journal_obj:
        raise HTTPException(status_code=404, detail="Journal not found")
    
    return {
        "id": journal_obj.id,
        "date": journal_obj.date,
        "content": journal_obj.content,
        "sections": [
            {
                "id": section.id,
                "name": section.name,
                "template_id": section.template_id,
                "field_values": [
                    {
                        "id": fv.id,
                        "label": fv.label,
                        "field_type": fv.field_type,
                        "value": fv.value
                    }
                    for fv in section.field_values
                ]
            }
            for section in journal_obj.journal_sections
        ]
    }

@app.get("/templates", response_model=List[dict])
async def get_existing_templates(
    db: db_session,
    token:str = Depends(oauth2_scheme)
):
    print("TOKEN:", token)
    # 1️⃣ Get current user
    current_user= await get_current_user(db, token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 2️⃣ Fetch templates for this user with fields (eager load)
    result = await db.execute(
        select(journal.SectionTemplate)
        .options(selectinload(journal.SectionTemplate.section_fields))
        .where(
            journal.SectionTemplate.user_id == current_user.id,
            journal.SectionTemplate.status == journal.TemplateStatus.ACTIVE
        )
    )
    templates = result.scalars().all()

    # 3️⃣ Convert to JSON-friendly dict
    output = []
    for t in templates:
        output.append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
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

@app.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(db, token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    result = await db.execute(
        select(journal.SectionTemplate)
        .where(journal.SectionTemplate.id == template_id)
        .where(journal.SectionTemplate.user_id == current_user.id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    template.status = journal.TemplateStatus.TERMINATED
    await db.commit()
    return {"message": "Template marked as inactive"}

from collections import defaultdict


@app.post("/journal")
async def create_journal(
    data: JournalCreate,
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(db, token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid token")

    new_journal = journal.Journal(
        user_id=current_user.id,
        date=data.date.replace(tzinfo=None),
        content=data.content
    )
    db.add(new_journal)
    await db.flush()
    sections_data = data.sections or []

    template_ids = [s.template_id for s in sections_data if s.template_id]

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

    for section_data in sections_data:
        section = journal.JournalSection(
            journal_id=new_journal.id,
            template_id=section_data.template_id,
            name=section_data.name
        )
        db.add(section)
        await db.flush()
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
                        field_type=field.field_type.value if isinstance(field.field_type, Enum) else field.field_type,
                        value=None
                    ))
            
            # If the user toggled reusable off for an existing template, mark it inactive.
            if not getattr(section_data, "reusable", True):
                db_template = await db.execute(
                    select(journal.SectionTemplate).where(journal.SectionTemplate.id == section_data.template_id)
                )
                template_to_update = db_template.scalar_one_or_none()
                if template_to_update:
                    template_to_update.status = journal.TemplateStatus.TERMINATED

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

            await db.flush()
            for fv, tf in zip(section_data.field_values or [], template_fields):
                fv.field_id = tf.id

            section.template_id = new_template.id

        for fv in section_data.field_values or []:
            db.add(journal.FieldValue(
                section_id=section.id,
                field_id=fv.field_id,
                label=fv.label,
                field_type=fv.field_type,
                value=fv.value
            ))

    await db.commit()

    await db.refresh(new_journal)
    return new_journal

@app.delete("/journal/{journal_id}")
async def delete_journal(
    db: db_session,
    journal_id: int = Path(..., description="ID of the journal to delete"),
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(db, token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid token")

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
    await db.commit()

    return  {"message":"Deleted successfully"}