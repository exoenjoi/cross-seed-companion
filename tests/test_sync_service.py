from dataclasses import dataclass, field

from app.config import Settings
from app.prowlarr import Indexer, Tag
from app.sync_service import apply_sync, compute_sync_preview


CONFIG_TEMPLATE = """module.exports = {{
  torznab: [
{urls}
  ],
  delay: 30,
}};
"""


class FakeProwlarr:
    def __init__(self, indexers: list[Indexer], tags: list[Tag]):
        self._indexers = indexers
        self._tags = tags

    def get_indexers(self) -> list[Indexer]:
        return self._indexers

    def get_tags(self) -> list[Tag]:
        return self._tags


def _settings(config_path, **overrides) -> Settings:
    values = {
        "PROWLARR_URL": "http://prowlarr:9696",
        "PROWLARR_API_KEY": "new-key",
        "CROSSSEED_URL": "http://cross-seed:2468",
        "CROSSSEED_API_KEY": "cs-key",
        "CROSSSEED_CONFIG_PATH": str(config_path.parent),
    }
    return Settings(_env_file=None, **{k.lower(): v for k, v in values.items()}, **overrides)


def _write_config(tmp_path, existing_ids):
    urls = "\n".join(
        f'    "http://prowlarr:9696/{i}/api?apikey=old",' for i in existing_ids
    )
    config_path = tmp_path / "config.js"
    config_path.write_text(CONFIG_TEMPLATE.format(urls=urls))
    return config_path


def test_compute_sync_preview_reports_added_and_removed(tmp_path):
    config_path = _write_config(tmp_path, existing_ids=[1, 2])
    prowlarr = FakeProwlarr(
        indexers=[
            Indexer(id=1, name="A", enable=True, privacy="private", tags=[]),
            Indexer(id=3, name="B", enable=True, privacy="private", tags=[]),
        ],
        tags=[],
    )
    settings = _settings(config_path)

    preview = compute_sync_preview(prowlarr, settings)

    assert preview.added == ["http://prowlarr:9696/3/api?apikey=new-key"]
    assert preview.removed == ["http://prowlarr:9696/2/api?apikey=old"]
    # config.js reste inchangé après un simple preview
    assert "old" in config_path.read_text()


def test_apply_sync_writes_backup_and_new_config(tmp_path):
    config_path = _write_config(tmp_path, existing_ids=[1, 2])
    prowlarr = FakeProwlarr(
        indexers=[Indexer(id=3, name="B", enable=True, privacy="private", tags=[])],
        tags=[],
    )
    settings = _settings(config_path)

    preview = apply_sync(prowlarr, settings)

    assert preview.new_urls == ["http://prowlarr:9696/3/api?apikey=new-key"]
    new_text = config_path.read_text()
    assert "http://prowlarr:9696/3/api?apikey=new-key" in new_text
    assert "old" not in new_text

    backups = list(tmp_path.glob("config.js.bak.*"))
    assert len(backups) == 1
    assert "old" in backups[0].read_text()


def test_apply_sync_excludes_public_and_tagged_indexers(tmp_path):
    config_path = _write_config(tmp_path, existing_ids=[])
    prowlarr = FakeProwlarr(
        indexers=[
            Indexer(id=1, name="Private", enable=True, privacy="private", tags=[]),
            Indexer(id=2, name="Public", enable=True, privacy="public", tags=[]),
            Indexer(id=3, name="Tagged", enable=True, privacy="private", tags=[10]),
        ],
        tags=[Tag(id=10, label="no-cross-seed")],
    )
    settings = _settings(
        config_path,
        sync_exclude_public=True,
        sync_exclude_tag="no-cross-seed",
    )

    preview = apply_sync(prowlarr, settings)

    assert preview.new_urls == ["http://prowlarr:9696/1/api?apikey=new-key"]


def test_compute_sync_preview_with_prowlarr_url_path_prefix(tmp_path):
    """Test that URL parsing handles PROWLARR_URL with path prefix."""
    base_url_with_path = "http://prowlarr:9696/prowlarr"
    # Config has URLs with path prefix matching the prowlarr_url
    urls = "\n".join(
        f'    "{base_url_with_path}/{i}/api?apikey=old",' for i in [1, 2]
    )
    config_path = tmp_path / "config.js"
    config_path.write_text(CONFIG_TEMPLATE.format(urls=urls))

    prowlarr = FakeProwlarr(
        indexers=[
            Indexer(id=1, name="A", enable=True, privacy="private", tags=[]),
            Indexer(id=3, name="B", enable=True, privacy="private", tags=[]),
        ],
        tags=[],
    )
    # Create settings with the path-prefixed URL
    values = {
        "PROWLARR_URL": base_url_with_path,
        "PROWLARR_API_KEY": "new-key",
        "CROSSSEED_URL": "http://cross-seed:2468",
        "CROSSSEED_API_KEY": "cs-key",
        "CROSSSEED_CONFIG_PATH": str(config_path.parent),
    }
    settings = Settings(_env_file=None, **{k.lower(): v for k, v in values.items()})

    preview = compute_sync_preview(prowlarr, settings)

    assert preview.added == [f"{base_url_with_path}/3/api?apikey=new-key"]
    assert preview.removed == [f"{base_url_with_path}/2/api?apikey=old"]
    # config.js reste inchangé après un simple preview
    assert "old" in config_path.read_text()


def test_compute_sync_preview_treats_unparseable_current_url_as_removed(tmp_path):
    """A config.js written by hand (or by another tool) can contain URLs that
    don't match Prowlarr's /{id}/api? shape at all, e.g. a Jackett-style
    indexer URL. This must not raise — it should be reported as removed,
    since the flat-array replacement will in fact drop it on apply."""
    jackett_url = "http://jackett:9117/api/v2.0/indexers/x/results/torznab/"
    config_path = tmp_path / "config.js"
    config_path.write_text(
        CONFIG_TEMPLATE.format(
            urls=(
                '    "http://prowlarr:9696/1/api?apikey=old",\n'
                f'    "{jackett_url}",'
            )
        )
    )
    prowlarr = FakeProwlarr(
        indexers=[Indexer(id=1, name="A", enable=True, privacy="private", tags=[])],
        tags=[],
    )
    settings = _settings(config_path)

    preview = compute_sync_preview(prowlarr, settings)

    assert preview.added == []
    assert preview.removed == [jackett_url]


def test_preview_not_noop_when_api_key_rotated_for_same_id(tmp_path):
    """Same indexer id on both sides but a different API key (rotation) must
    not be classified as a no-op, even though id-based added/removed are
    both empty."""
    config_path = _write_config(tmp_path, existing_ids=[1])
    prowlarr = FakeProwlarr(
        indexers=[Indexer(id=1, name="A", enable=True, privacy="private", tags=[])],
        tags=[],
    )
    settings = _settings(config_path)  # prowlarr_api_key="new-key" vs config's "old"

    preview = compute_sync_preview(prowlarr, settings)

    assert preview.added == []
    assert preview.removed == []
    assert preview.current_urls != preview.new_urls


def test_apply_sync_skips_backup_and_write_when_truly_noop(tmp_path):
    config_path = _write_config(tmp_path, existing_ids=[1])
    prowlarr = FakeProwlarr(
        indexers=[Indexer(id=1, name="A", enable=True, privacy="private", tags=[])],
        tags=[],
    )
    settings = Settings(
        _env_file=None,
        prowlarr_url="http://prowlarr:9696",
        prowlarr_api_key="old",  # matches the config's existing key -> true no-op
        crossseed_url="http://cross-seed:2468",
        crossseed_api_key="cs-key",
        crossseed_config_path=str(config_path.parent),
    )
    original_text = config_path.read_text()

    preview = apply_sync(prowlarr, settings)

    assert preview.current_urls == preview.new_urls
    assert config_path.read_text() == original_text
    assert list(tmp_path.glob("config.js.bak.*")) == []
