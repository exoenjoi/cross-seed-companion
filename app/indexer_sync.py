from app.prowlarr import Indexer, Tag


def resolve_excluded_tag_id(tags: list[Tag], tag_name: str | None) -> int | None:
    if tag_name is None:
        return None
    for tag in tags:
        if tag.label == tag_name:
            return tag.id
    return None


def filter_indexers(
    indexers: list[Indexer],
    exclude_public: bool,
    excluded_tag_id: int | None,
) -> list[Indexer]:
    result = []
    for indexer in indexers:
        if not indexer.enable:
            continue
        if exclude_public and indexer.privacy == "public":
            continue
        if excluded_tag_id is not None and excluded_tag_id in indexer.tags:
            continue
        result.append(indexer)
    return result


def build_torznab_urls(
    prowlarr_url: str,
    prowlarr_api_key: str,
    indexer_ids: list[int],
) -> list[str]:
    base = prowlarr_url.rstrip("/")
    return [f"{base}/{indexer_id}/api?apikey={prowlarr_api_key}" for indexer_id in indexer_ids]


def compute_diff(old_urls: list[str], new_urls: list[str]) -> tuple[list[str], list[str]]:
    old_set = set(old_urls)
    new_set = set(new_urls)
    added = sorted(new_set - old_set)
    removed = sorted(old_set - new_set)
    return added, removed
