from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.prowlarr import Indexer, Tag
from app.routers import sync as sync_router


CONFIG_TEXT = """module.exports = {
  torznab: [
    "http://prowlarr:9696/1/api?apikey=old"
  ],
  delay: 30,
};
"""


class FakeProwlarr:
    def __init__(self, indexers, tags):
        self._indexers = indexers
        self._tags = tags

    def get_indexers(self):
        return self._indexers

    def get_tags(self):
        return self._tags


def _client(tmp_path, indexers, tags=None, prowlarr_api_key="new-key") -> TestClient:
    config_path = tmp_path / "config.js"
    config_path.write_text(CONFIG_TEXT)

    app = FastAPI()
    app.include_router(sync_router.router)
    app.state.settings = Settings(
        _env_file=None,
        prowlarr_url="http://prowlarr:9696",
        prowlarr_api_key=prowlarr_api_key,
        crossseed_url="http://cross-seed:2468",
        crossseed_api_key="cs-key",
        crossseed_config_path=str(tmp_path),
    )
    app.state.prowlarr_client = FakeProwlarr(indexers, tags or [])
    return TestClient(app)


def test_get_sync_shows_diff_preview(tmp_path):
    client = _client(
        tmp_path,
        indexers=[Indexer(id=2, name="B", enable=True, privacy="private", tags=[])],
    )

    response = client.get("/sync")

    assert response.status_code == 200
    assert "http://prowlarr:9696/2/api?apikey=new-key" in response.text
    assert "Confirm and apply" in response.text


def test_get_sync_shows_indexer_name_next_to_url(tmp_path):
    client = _client(
        tmp_path,
        indexers=[Indexer(id=2, name="The Old School", enable=True, privacy="private", tags=[])],
    )

    response = client.get("/sync")

    assert response.status_code == 200
    assert '<span class="idx-name">The Old School</span>' in response.text
    assert "http://prowlarr:9696/2/api" in response.text


def test_get_sync_shows_id_privacy_and_added_date_next_to_indexer(tmp_path):
    client = _client(
        tmp_path,
        indexers=[
            Indexer(id=2, name="B", enable=True, privacy="private", tags=[], added="2025-12-28T10:15:00Z")
        ],
    )

    response = client.get("/sync")

    assert response.status_code == 200
    assert "ID 2" in response.text
    assert "private" in response.text
    assert "added 2025-12-28" in response.text


def test_get_sync_masks_long_api_keys_in_diff_table(tmp_path):
    client = _client(
        tmp_path,
        indexers=[Indexer(id=2, name="B", enable=True, privacy="private", tags=[])],
        prowlarr_api_key="ce571e6a7f804d5e83993f077a963c05",
    )

    response = client.get("/sync")

    assert response.status_code == 200
    assert "ce571e6a7f804d5e83993f077a963c05" not in response.text
    assert "apikey=ce571e6a…" in response.text


def test_get_sync_lists_current_indexers_when_only_key_rotated(tmp_path):
    """Same indexer id on both sides means added/removed are both empty, but
    the page must still list the current indexers by name instead of
    rendering nothing between the counts and the apply button."""
    client = _client(
        tmp_path,
        indexers=[Indexer(id=1, name="A", enable=True, privacy="private", tags=[])],
    )

    response = client.get("/sync")

    assert response.status_code == 200
    assert '<span class="idx-name">A</span>' in response.text
    assert "http://prowlarr:9696/1/api?apikey=new-key" in response.text


def test_get_sync_lists_unchanged_indexers_below_the_diff(tmp_path):
    """When a real diff exists (e.g. one indexer tagged out), the page must
    still show the indexers that stay synced, not just what's changing."""
    config_path = tmp_path / "config.js"
    config_path.write_text(
        "module.exports = {\n"
        '  torznab: [\n'
        '    "http://prowlarr:9696/1/api?apikey=old",\n'
        '    "http://prowlarr:9696/2/api?apikey=old"\n'
        '  ],\n'
        "  delay: 30,\n"
        "};\n"
    )
    app = FastAPI()
    app.include_router(sync_router.router)
    app.state.settings = Settings(
        _env_file=None,
        prowlarr_url="http://prowlarr:9696",
        prowlarr_api_key="new-key",
        crossseed_url="http://cross-seed:2468",
        crossseed_api_key="cs-key",
        crossseed_config_path=str(tmp_path),
    )
    app.state.prowlarr_client = FakeProwlarr(
        indexers=[
            Indexer(id=1, name="Kept", enable=True, privacy="private", tags=[]),
            Indexer(id=3, name="New", enable=True, privacy="private", tags=[]),
        ],
        tags=[],
    )

    response = TestClient(app).get("/sync")

    assert response.status_code == 200
    assert '<span class="idx-name">New</span>' in response.text
    assert "Already synced (1):" in response.text
    assert '<span class="idx-name">Kept</span>' in response.text


def test_post_sync_apply_writes_config_and_confirms(tmp_path):
    client = _client(
        tmp_path,
        indexers=[Indexer(id=2, name="B", enable=True, privacy="private", tags=[])],
    )

    response = client.post("/sync/apply")

    assert response.status_code == 200
    assert "applied" in response.text
    assert (tmp_path / "config.js").read_text().count("http://prowlarr:9696/2/api?apikey=new-key") == 1


def test_get_sync_shows_apply_form_when_only_api_key_rotated(tmp_path):
    """Same indexer id (1) on both sides but a rotated API key must still
    surface the apply form, not the 'Already in sync' no-op message."""
    client = _client(
        tmp_path,
        indexers=[Indexer(id=1, name="A", enable=True, privacy="private", tags=[])],
    )

    response = client.get("/sync")

    assert response.status_code == 200
    assert "Already in sync" not in response.text
    assert "Confirm and apply" in response.text


def test_get_sync_shows_error_when_torznab_block_missing(tmp_path):
    (tmp_path / "config.js").write_text("module.exports = { delay: 30 };")
    client = FastAPI()
    client.include_router(sync_router.router)
    client.state.settings = Settings(
        _env_file=None,
        prowlarr_url="http://prowlarr:9696",
        prowlarr_api_key="new-key",
        crossseed_url="http://cross-seed:2468",
        crossseed_api_key="cs-key",
        crossseed_config_path=str(tmp_path),
    )
    client.state.prowlarr_client = FakeProwlarr(indexers=[], tags=[])

    response = TestClient(client).get("/sync")

    assert response.status_code == 200
    assert "Error" in response.text
    # Full-page GET error must render inside the app shell (base.html), not
    # as a naked unstyled fragment.
    assert "Cross-Seed Companion" in response.text
