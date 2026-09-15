from pathlib import Path

import httpx
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.crossseed_config import TorznabBlockError
from app.sync_service import apply_sync, compute_sync_preview

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/sync")
def sync_page(request: Request):
    settings = request.app.state.settings
    prowlarr = request.app.state.prowlarr_client
    try:
        preview = compute_sync_preview(prowlarr, settings)
    except (TorznabBlockError, OSError, httpx.HTTPError, ValueError) as exc:
        return templates.TemplateResponse(request, "_error_page.html", {"message": str(exc)})
    return templates.TemplateResponse(
        request, "sync.html", {"preview": preview, "applied": False, "settings": settings}
    )


@router.post("/sync/apply")
def sync_apply(request: Request):
    settings = request.app.state.settings
    prowlarr = request.app.state.prowlarr_client
    try:
        preview = apply_sync(prowlarr, settings)
    except (TorznabBlockError, OSError, httpx.HTTPError, ValueError) as exc:
        return templates.TemplateResponse(request, "_error.html", {"message": str(exc)})
    return templates.TemplateResponse(
        request, "_sync_result.html", {"preview": preview, "applied": True, "settings": settings}
    )
