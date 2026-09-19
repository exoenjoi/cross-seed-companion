from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.routers import actions as actions_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(actions_router.router)
    app.state.settings = Settings(
        _env_file=None,
        prowlarr_url="http://prowlarr:9696",
        prowlarr_api_key="prow-key",
        crossseed_url="http://cross-seed:2468",
        crossseed_api_key="cs-key",
        crossseed_config_path="/config",
    )
    return TestClient(app)


def test_footer_shows_the_version_baked_into_the_image(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "v9.9.9")

    response = _client().get("/actions")

    assert "v9.9.9" in response.text


def test_footer_falls_back_to_dev_when_no_version_is_set(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)

    response = _client().get("/actions")

    assert "dev" in response.text.split("<footer", 1)[1]
