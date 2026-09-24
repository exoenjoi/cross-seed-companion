from datetime import date

from fastapi import APIRouter, Request

from app.crossseed_events import group_events, summarize
from app.log_history import read_all_events
from app.log_paths import resolve_logs_dir
from app.templates import templates

router = APIRouter()


def _load_context(request: Request):
    settings = request.app.state.settings
    logs_dir = resolve_logs_dir(settings)
    if not logs_dir.exists():
        return None, f"Logs not found: {logs_dir}. Check the logs/ bind mount."
    grouped = group_events(read_all_events(logs_dir))
    return {"grouped": grouped, "stats": summarize(grouped, date.today())}, None


@router.get("/added")
def added_page(request: Request):
    context, error = _load_context(request)
    if error:
        return templates.TemplateResponse(request, "_error_page.html", {"message": error})
    return templates.TemplateResponse(request, "added.html", context)


@router.get("/added/refresh")
def added_refresh(request: Request):
    context, error = _load_context(request)
    if error:
        return templates.TemplateResponse(request, "_error.html", {"message": error})
    return templates.TemplateResponse(request, "_added_list.html", context)
