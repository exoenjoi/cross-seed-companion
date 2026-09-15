import re
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.crossseed_config import (
    backup_config,
    extract_current_urls,
    read_config,
    replace_torznab_block,
    write_config,
)
from app.indexer_sync import (
    build_torznab_urls,
    filter_indexers,
    resolve_excluded_tag_id,
)
from app.prowlarr import ProwlarrClient


@dataclass
class SyncPreview:
    current_urls: list[str]
    new_urls: list[str]
    added: list[str]
    removed: list[str]


def _config_path(settings: Settings) -> Path:
    return Path(settings.crossseed_config_path) / "config.js"


def _extract_indexer_id(url: str) -> int | None:
    """Extract indexer ID from a Prowlarr torznab URL.

    Matches the pattern /{id}/api? in the URL to handle any base URL shape,
    including those with path prefixes (e.g. http://host/prowlarr/{id}/api?...).
    Returns None when the URL doesn't match this shape (e.g. a Jackett-style
    URL, or anything else a user's real config.js might contain) instead of
    raising — current_urls comes from arbitrary user config and must never
    crash the diff.
    """
    match = re.search(r'/(\d+)/api\?', url)
    return int(match.group(1)) if match else None


def _build_new_urls(prowlarr: ProwlarrClient, settings: Settings) -> list[str]:
    indexers = prowlarr.get_indexers()
    tags = prowlarr.get_tags()
    excluded_tag_id = resolve_excluded_tag_id(tags, settings.sync_exclude_tag)
    kept = filter_indexers(
        indexers,
        exclude_public=settings.sync_exclude_public,
        excluded_tag_id=excluded_tag_id,
    )
    return build_torznab_urls(
        settings.prowlarr_url,
        settings.prowlarr_api_key,
        [indexer.id for indexer in kept],
    )


def _compute_diff_by_id(current_urls: list[str], new_urls: list[str]) -> tuple[list[str], list[str]]:
    """Compute added and removed URLs based on indexer IDs, not full URLs.

    This allows comparing URLs with different API keys.
    """
    # Map indexer ID to URL. A current-side URL whose ID can't be parsed
    # (e.g. Jackett-shaped, or any other shape a real config.js might hold)
    # is unconditionally "removed": it's not one of the new indexer-managed
    # URLs, and the flat-array replacement will drop it on apply anyway.
    current_by_id: dict[int, str] = {}
    unparseable_current: list[str] = []
    for url in current_urls:
        indexer_id = _extract_indexer_id(url)
        if indexer_id is None:
            unparseable_current.append(url)
        else:
            current_by_id[indexer_id] = url
    new_by_id = {_extract_indexer_id(url): url for url in new_urls}

    # Find added and removed IDs
    added_ids = set(new_by_id.keys()) - set(current_by_id.keys())
    removed_ids = set(current_by_id.keys()) - set(new_by_id.keys())

    # Map back to URLs and sort
    added = sorted(new_by_id[id] for id in added_ids)
    removed = sorted([current_by_id[id] for id in removed_ids] + unparseable_current)

    return added, removed


def compute_sync_preview(prowlarr: ProwlarrClient, settings: Settings) -> SyncPreview:
    config_text = read_config(_config_path(settings))
    current_urls = extract_current_urls(config_text)
    new_urls = _build_new_urls(prowlarr, settings)
    added, removed = _compute_diff_by_id(current_urls, new_urls)
    return SyncPreview(current_urls=current_urls, new_urls=new_urls, added=added, removed=removed)


def apply_sync(prowlarr: ProwlarrClient, settings: Settings) -> SyncPreview:
    config_path = _config_path(settings)
    config_text = read_config(config_path)
    current_urls = extract_current_urls(config_text)
    new_urls = _build_new_urls(prowlarr, settings)
    added, removed = _compute_diff_by_id(current_urls, new_urls)

    if new_urls == current_urls:
        # Nothing actually changed (true no-op) — skip the needless backup+write.
        return SyncPreview(current_urls=current_urls, new_urls=new_urls, added=added, removed=removed)

    backup_config(config_path)
    write_config(config_path, replace_torznab_block(config_text, new_urls))

    return SyncPreview(current_urls=current_urls, new_urls=new_urls, added=added, removed=removed)
