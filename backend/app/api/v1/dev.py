# api/v1/dev.py  –  Dev-only endpoints (only mounted in ENVIRONMENT=development)
#
# GET  /api/v1/dev/email-previews           → JSON list of saved preview files
# GET  /api/v1/dev/email-previews/latest    → serve/download the most recent HTML
# GET  /api/v1/dev/email-previews/{filename} → serve a specific HTML file
# POST /api/v1/dev/trigger-reminder-email   → generate a sample reminder email right now

import pathlib
import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from services.email import _build_reminder_html, _dev_save_html, _DEV_PREVIEW_DIR, _task_url, _journal_url

app = APIRouter()


def _list_previews() -> list[dict]:
    if not _DEV_PREVIEW_DIR.exists():
        return []
    files = sorted(_DEV_PREVIEW_DIR.glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True)
    return [
        {
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "created_at": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            "url": f"/api/v1/dev/email-previews/{f.name}",
        }
        for f in files
    ]


@app.get("/dev/email-previews", tags=["Dev"])
def list_email_previews():
    """List all saved email HTML previews."""
    return {"previews": _list_previews()}


@app.get("/dev/email-previews/latest", response_class=HTMLResponse, tags=["Dev"])
def latest_email_preview():
    """Open the most recently generated email HTML in the browser."""
    previews = _list_previews()
    if not previews:
        raise HTTPException(status_code=404, detail="No email previews found. Trigger an email first.")
    filepath = _DEV_PREVIEW_DIR / previews[0]["filename"]
    return HTMLResponse(content=filepath.read_text(encoding="utf-8"))


@app.get("/dev/email-previews/{filename}", response_class=HTMLResponse, tags=["Dev"])
def get_email_preview(filename: str):
    """Open a specific email HTML preview in the browser."""
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    filepath = _DEV_PREVIEW_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Preview '{filename}' not found.")
    return HTMLResponse(content=filepath.read_text(encoding="utf-8"))


@app.post("/dev/trigger-reminder-email", tags=["Dev"])
def trigger_reminder_email(
    type: str = "task",
    task_title: str = "Buy groceries before 6pm",
    task_description: str = "Pick up eggs, milk, vegetables, and coffee beans.",
    task_id: int = 42,
):
    """
    Generate a sample reminder email and save it as an HTML preview.

    - **type**: `task` or `journal`
    - Returns the preview URL to open in browser.
    """
    if type == "task":
        cta_url = _task_url(task_id)
        html = _build_reminder_html(
            title="Task Reminder",
            subtitle=task_title,
            body_text=task_description,
            icon="\u2705",
            cta_url=cta_url,
            cta_label="Open Task \u2192",
            task_title=task_title,
            is_task=True,
        )
        label = "task_reminder"
        subject = f"Task Reminder: {task_title}"
    else:
        html = _build_reminder_html(
            title="Daily Journal Reminder",
            subtitle="Don\u2019t forget to write your progress!",
            body_text="Every day counts. Keep up the good work and jot down your thoughts today.",
            icon="\U0001f4d3",
            cta_url="",
            cta_label="Write Today\u2019s Journal \u2192",
        )
        label = "journal_reminder"
        subject = "Daily Journal Reminder"

    filepath = _dev_save_html(subject, "dev@preview.local", html, label)
    filename = pathlib.Path(filepath).name

    return JSONResponse({
        "saved_to": filepath,
        "preview_url": f"/api/v1/dev/email-previews/{filename}",
        "tip": "Open preview_url in your browser to see the email.",
    })
