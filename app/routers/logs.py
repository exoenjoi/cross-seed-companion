import asyncio
from pathlib import Path
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import Settings
from app.log_history import list_available_days, read_day_entries
from app.log_paths import CURRENT_LOG_FILENAME, resolve_logs_dir
from app.log_tailer import LogTailer, read_recent_entries
from app.templates import templates

router = APIRouter()


def _current_log_path(settings: Settings) -> Path:
    return resolve_logs_dir(settings) / CURRENT_LOG_FILENAME


def format_sse_event(html: str) -> str:
    return "".join(f"data: {line}\n" for line in html.splitlines()) + "\n"


async def sse_log_stream(
    tailer: LogTailer,
    request: Request,
    poll_interval: float = 1.0,
) -> AsyncIterator[str]:
    try:
        while True:
            if await request.is_disconnected():
                break
            for entry in tailer.read_new_entries():
                html = templates.get_template("_log_line.html").render(entry=entry)
                yield format_sse_event(html)
            await asyncio.sleep(poll_interval)
    finally:
        tailer.close()


@router.get("/logs")
def logs_page(request: Request, day: str | None = None):
    settings = request.app.state.settings
    logs_dir = resolve_logs_dir(settings)
    available_days = list_available_days(logs_dir)

    if day is not None and day in available_days:
        entries = read_day_entries(logs_dir, day)
        return templates.TemplateResponse(
            request,
            "logs.html",
            {"entries": entries, "available_days": available_days, "selected_day": day},
        )

    path = _current_log_path(settings)
    if not path.exists():
        return templates.TemplateResponse(
            request,
            "_error_page.html",
            {"message": f"Logs not found: {path}. Check the logs/ bind mount."},
        )
    entries = read_recent_entries(path, max_entries=200)
    return templates.TemplateResponse(
        request,
        "logs.html",
        {"entries": entries, "available_days": available_days, "selected_day": "current"},
    )


@router.get("/logs/stream")
async def logs_stream(request: Request):
    settings = request.app.state.settings
    path = _current_log_path(settings)
    tailer = LogTailer(path)
    return StreamingResponse(sse_log_stream(tailer, request), media_type="text/event-stream")
