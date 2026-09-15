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


def _client(tmp_path, indexers, tags=None) -> TestClient:
    config_path = tmp_path / "config.js"
    config_path.write_text(CONFIG_TEXT)

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
    assert "Confirmer et appliquer" in response.text


def test_post_sync_apply_writes_config_and_confirms(tmp_path):
    client = _client(
        tmp_path,
        indexers=[Indexer(id=2, name="B", enable=True, privacy="private", tags=[])],
    )

    response = client.post("/sync/apply")

    assert response.status_code == 200
    assert "appliquée" in response.text
    assert (tmp_path / "config.js").read_text().count("http://prowlarr:9696/2/api?apikey=new-key") == 1


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
    assert "Erreur" in response.text
