from app.indexer_sync import (
    build_torznab_urls,
    filter_indexers,
    resolve_excluded_tag_id,
)
from app.prowlarr import Indexer, Tag


def test_resolve_excluded_tag_id_finds_matching_label():
    tags = [Tag(id=10, label="no-cross-seed"), Tag(id=11, label="anime")]
    assert resolve_excluded_tag_id(tags, "no-cross-seed") == 10


def test_resolve_excluded_tag_id_returns_none_when_not_configured():
    tags = [Tag(id=10, label="no-cross-seed")]
    assert resolve_excluded_tag_id(tags, None) is None


def test_resolve_excluded_tag_id_returns_none_when_label_unknown():
    tags = [Tag(id=10, label="no-cross-seed")]
    assert resolve_excluded_tag_id(tags, "does-not-exist") is None


def test_filter_indexers_excludes_disabled_public_and_tagged():
    indexers = [
        Indexer(id=1, name="Private", enable=True, privacy="private", tags=[]),
        Indexer(id=2, name="Public", enable=True, privacy="public", tags=[]),
        Indexer(id=3, name="Disabled", enable=False, privacy="private", tags=[]),
        Indexer(id=4, name="Tagged", enable=True, privacy="private", tags=[10]),
    ]

    result = filter_indexers(indexers, exclude_public=True, excluded_tag_id=10)

    assert [i.id for i in result] == [1]


def test_filter_indexers_keeps_public_when_not_excluded():
    indexers = [Indexer(id=1, name="Public", enable=True, privacy="public", tags=[])]

    result = filter_indexers(indexers, exclude_public=False, excluded_tag_id=None)

    assert [i.id for i in result] == [1]


def test_build_torznab_urls_formats_official_crossseed_pattern():
    urls = build_torznab_urls("http://prowlarr:9696/", "prowlarr-key", [1, 6, 22])

    assert urls == [
        "http://prowlarr:9696/1/api?apikey=prowlarr-key",
        "http://prowlarr:9696/6/api?apikey=prowlarr-key",
        "http://prowlarr:9696/22/api?apikey=prowlarr-key",
    ]
