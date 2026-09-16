from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.log_history import read_all_events
from app.log_paths import resolve_logs_dir

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/added")
def added_page(request: Request):
    settings = request.app.state.settings
    logs_dir = resolve_logs_dir(settings)
    if not logs_dir.exists():
        return templates.TemplateResponse(
            request,
            "_error_page.html",
            {"message": f"Logs not found: {logs_dir}. Check the logs/ bind mount."},
        )
    events = read_all_events(logs_dir)
    return templates.TemplateResponse(request, "added.html", {"events": events})
