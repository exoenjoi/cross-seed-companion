import asyncio
from pathlib import Path
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

from app.config import Settings
from app.log_tailer import LogTailer, read_recent_entries

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _current_log_path(settings: Settings) -> Path:
    logs_dir = settings.crossseed_logs_path or (settings.crossseed_config_path / "logs")
    return Path(logs_dir) / "verbose.current.log"


def format_sse_event(html: str) -> str:
    return "".join(f"data: {line}\n" for line in html.split("\n")) + "\n"


async def sse_log_stream(
    tailer: LogTailer,
    request: Request,
    poll_interval: float = 1.0,
) -> AsyncIterator[str]:
    while True:
        if await request.is_disconnected():
            break
        for entry in tailer.read_new_entries():
            html = templates.get_template("_log_line.html").render(entry=entry)
            yield format_sse_event(html)
        await asyncio.sleep(poll_interval)


@router.get("/logs")
def logs_page(request: Request):
    settings = request.app.state.settings
    path = _current_log_path(settings)
    if not path.exists():
        return templates.TemplateResponse(
            request,
            "_error_page.html",
            {"message": f"Logs introuvables : {path}. Vérifiez le bind mount de logs/."},
        )
    entries = read_recent_entries(path, max_entries=200)
    return templates.TemplateResponse(request, "logs.html", {"entries": entries})


@router.get("/logs/stream")
async def logs_stream(request: Request):
    settings = request.app.state.settings
    path = _current_log_path(settings)
    tailer = LogTailer(path)
    return StreamingResponse(sse_log_stream(tailer, request), media_type="text/event-stream")
