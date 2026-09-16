from fastapi import APIRouter, Request

from app.crossseed_events import group_events_by_name
from app.log_history import read_all_events
from app.log_paths import resolve_logs_dir
from app.templates import templates

router = APIRouter()


def _load_grouped(request: Request):
    settings = request.app.state.settings
    logs_dir = resolve_logs_dir(settings)
    if not logs_dir.exists():
        return None, f"Logs not found: {logs_dir}. Check the logs/ bind mount."
    grouped = group_events_by_name(read_all_events(logs_dir))
    return grouped, None


@router.get("/added")
def added_page(request: Request):
    grouped, error = _load_grouped(request)
    if error:
        return templates.TemplateResponse(request, "_error_page.html", {"message": error})
    return templates.TemplateResponse(request, "added.html", {"grouped": grouped})


@router.get("/added/refresh")
def added_refresh(request: Request):
    grouped, error = _load_grouped(request)
    if error:
        return templates.TemplateResponse(request, "_error.html", {"message": error})
    return templates.TemplateResponse(request, "_added_list.html", {"grouped": grouped})
