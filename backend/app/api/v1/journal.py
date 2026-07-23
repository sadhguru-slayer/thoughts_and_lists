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
from schema.Journal import JournalCreate, JournalResponse, JournalUpdate
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


from datetime import datetime, timedelta
from collections import defaultdict

@app.get("/journal/analytics")
async def get_journal_analytics(
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(db, token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid token")

    journal_result = await db.execute(
        select(journal.Journal)
        .where(journal.Journal.user_id == current_user.id)
        .order_by(journal.Journal.date.desc())
    )
    journals = journal_result.scalars().all()
    thought_result = await db.execute(
        select(models.Thought).where(models.Thought.user_id == current_user.id)
    )
    thoughts = thought_result.scalars().all()

    total_journals = len(journals)
    total_words = sum(len(str(j.content).split()) for j in journals if j.content)
    
    daily_map = defaultdict(
        lambda: {
            "journal_created": 0,
            "journal_edited": 0,
            "thought_created": 0,
            "thought_edited": 0,
        }
    )

    def _to_day_str(dt_value):
        if not dt_value:
            return None
        if hasattr(dt_value, "strftime"):
            return dt_value.strftime("%Y-%m-%d")
        return str(dt_value)[:10]

    def _add_counter(day_str, key):
        if not day_str:
            return
        daily_map[day_str][key] += 1

    for j in journals:
        created_day = _to_day_str(getattr(j, "created_at", None) or j.date)
        edited_day = _to_day_str(getattr(j, "updated_at", None))
        _add_counter(created_day, "journal_created")
        if edited_day and edited_day != created_day:
            _add_counter(edited_day, "journal_edited")

    for t in thoughts:
        created_day = _to_day_str(getattr(t, "created_at", None))
        edited_day = _to_day_str(getattr(t, "updated_at", None))
        _add_counter(created_day, "thought_created")
        if edited_day and edited_day != created_day:
            _add_counter(edited_day, "thought_edited")

    daily_counts = []
    for day in sorted(daily_map.keys()):
        day_data = daily_map[day]
        total_actions = (
            day_data["journal_created"]
            + day_data["journal_edited"]
            + day_data["thought_created"]
            + day_data["thought_edited"]
        )
        daily_counts.append(
            {
                "date": day,
                "count": total_actions,
                "total_actions": total_actions,
                **day_data,
            }
        )

    unique_dates = sorted(list(daily_map.keys()), reverse=True)
    
    current_streak = 0
    longest_streak = 0
    
    if unique_dates:
        temp_longest = 1
        for i in range(len(unique_dates) - 1):
            d1 = datetime.strptime(unique_dates[i], "%Y-%m-%d")
            d2 = datetime.strptime(unique_dates[i+1], "%Y-%m-%d")
            if (d1 - d2).days == 1:
                temp_longest += 1
            else:
                longest_streak = max(longest_streak, temp_longest)
                temp_longest = 1
        longest_streak = max(longest_streak, temp_longest)
        
        today_date = datetime.utcnow().date()
        date_candidates = [
            (today_date + timedelta(days=1)).strftime("%Y-%m-%d"),
            today_date.strftime("%Y-%m-%d"),
            (today_date - timedelta(days=1)).strftime("%Y-%m-%d")
        ]
        
        if unique_dates[0] in date_candidates:
            current_streak = 1
            for i in range(len(unique_dates) - 1):
                d1 = datetime.strptime(unique_dates[i], "%Y-%m-%d")
                d2 = datetime.strptime(unique_dates[i+1], "%Y-%m-%d")
                if (d1 - d2).days == 1:
                    current_streak += 1
                else:
                    break
                    
    return {
        "total_journals": total_journals,
        "total_words": total_words,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_thoughts": len(thoughts),
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

@app.get("/journal/structure/latest")
async def get_latest_journal_structure(
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
            .selectinload(journal.JournalSection.field_values),
            selectinload(journal.Journal.journal_sections)
            .selectinload(journal.JournalSection.template)
        )
        .where(journal.Journal.user_id == current_user.id)
        .order_by(journal.Journal.date.desc())
        .limit(1)
    )

    latest_journal = result.scalar_one_or_none()

    if not latest_journal:
        return {"sections": []}

    active_sections = []
    for section in latest_journal.journal_sections:
        if not section.template_id:
            continue
        if section.template and section.template.status != journal.TemplateStatus.ACTIVE:
            continue
            
        active_sections.append({
            "name": section.name,
            "template_id": section.template_id,
            "fields": [
                {
                    "label": fv.label,
                    "field_type": fv.field_type,
                    "value": None  # reset value
                }
                for fv in section.field_values
            ]
        })

    return {
        "sections": active_sections
    }


@app.get("/templates", response_model=List[dict])
async def get_existing_templates(
    db: db_session,
    token:str = Depends(oauth2_scheme)
):
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
            max_order = max([f.order for f in template_fields], default=-1) if template_fields else -1
            for fv in section_data.field_values or []:
                if not fv.field_id:
                    max_order += 1
                    new_tf = journal.SectionField(
                        template_id=section_data.template_id,
                        label=fv.label,
                        field_type=fv.field_type,
                        order=max_order
                    )
                    db.add(new_tf)
                    await db.flush()
                    fv.field_id = new_tf.id
                    template_fields.append(new_tf)

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


@app.patch("/journal/{journal_id}")
async def update_journal(
    journal_id: int,
    data: JournalUpdate,
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

    has_updates = False
    if data.date is not None:
        journal_obj.date = data.date.replace(tzinfo=None)
        has_updates = True
    if data.content is not None:
        journal_obj.content = data.content
        has_updates = True

    section_map = {section.id: section for section in journal_obj.journal_sections}
    for section_data in data.sections or []:
        db_section = section_map.get(section_data.id)
        if not db_section:
            raise HTTPException(status_code=404, detail=f"Section {section_data.id} not found in journal")

        if section_data.name is not None:
            db_section.name = section_data.name
            has_updates = True

        field_map = {fv.id: fv for fv in db_section.field_values}
        for field_data in section_data.field_values or []:
            db_field = field_map.get(field_data.id)
            if not db_field:
                raise HTTPException(
                    status_code=404,
                    detail=f"Field value {field_data.id} not found in section {section_data.id}",
                )
            db_field.value = field_data.value
            has_updates = True

    if has_updates:
        journal_obj.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(journal_obj)
    return {"message": "Journal updated successfully"}

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