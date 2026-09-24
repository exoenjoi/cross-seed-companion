import re

import httpx
from fastapi import APIRouter, Request

from app.crossseed_config import TorznabBlockError
from app.prowlarr import Indexer
from app.sync_service import apply_sync, compute_sync_preview, extract_indexer_id
from app.templates import templates

router = APIRouter()

_API_KEY_RE = re.compile(r"(apikey=)([^&]+)")


def _indexer_for(url: str, indexers_by_id: dict[int, Indexer]) -> Indexer | None:
    indexer_id = extract_indexer_id(url)
    return indexers_by_id.get(indexer_id) if indexer_id is not None else None


def _mask_api_key(url: str) -> str:
    """Truncate the apikey= value so the diff table doesn't leak full keys."""

    def _mask(match: re.Match) -> str:
        key = match.group(2)
        if len(key) <= 8:
            return match.group(0)
        return f"{match.group(1)}{key[:8]}…"

    return _API_KEY_RE.sub(_mask, url)


templates.env.filters["indexer_for"] = _indexer_for
templates.env.filters["mask_api_key"] = _mask_api_key


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
        applied = apply_sync(prowlarr, settings)
        # Re-read config.js so the tables show what is now on disk, not the pre-apply diff.
        preview = compute_sync_preview(prowlarr, settings)
    except (TorznabBlockError, OSError, httpx.HTTPError, ValueError) as exc:
        return templates.TemplateResponse(request, "_error.html", {"message": str(exc)})
    return templates.TemplateResponse(
        request, "_sync_result.html", {"preview": preview, "applied": applied, "settings": settings}
    )
