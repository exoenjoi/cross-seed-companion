from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.routers import actions as actions_router


def _client(**settings_overrides) -> TestClient:
    app = FastAPI()
    app.include_router(actions_router.router)
    app.state.settings = Settings(
        _env_file=None,
        prowlarr_url="http://prowlarr:9696",
        prowlarr_api_key="prow-key",
        crossseed_url="http://cross-seed:2468",
        crossseed_api_key="cs-key",
        crossseed_config_path="/config",
        **settings_overrides,
    )
    return TestClient(app)


def test_get_actions_lists_builtin_actions():
    client = _client()

    response = client.get("/actions")

    assert response.status_code == 200
    assert "Lancer une recherche" in response.text
    assert "Notifier un infoHash" in response.text


def test_get_actions_shows_error_when_custom_file_invalid(tmp_path):
    bad_file = tmp_path / "custom.yml"
    bad_file.write_text("id: not-a-list\n")
    client = _client(actions_config_path=str(bad_file))

    response = client.get("/actions")

    assert response.status_code == 200
    assert "Erreur" in response.text


def test_get_actions_shows_error_when_custom_file_missing(tmp_path):
    missing_file = tmp_path / "does-not-exist.yml"
    client = _client(actions_config_path=str(missing_file))

    response = client.get("/actions")

    assert response.status_code == 200
    assert "Erreur" in response.text


def test_post_run_action_returns_result_fragment(monkeypatch):
    import httpx

    from app import action_runner

    def fake_run_action(action, settings, user_input=None, transport=None):
        return action_runner.ActionResult(ok=True, status_code=200, body="ok")

    monkeypatch.setattr(actions_router, "run_action", fake_run_action)
    client = _client()

    response = client.post("/actions/search/run")

    assert response.status_code == 200
    assert "search" not in response.text or "HTTP 200" in response.text
    assert "HTTP 200" in response.text


def test_post_run_action_unknown_id_returns_error_fragment():
    client = _client()

    response = client.post("/actions/does-not-exist/run")

    assert response.status_code == 200
    assert "Erreur" in response.text
    assert "does-not-exist" in response.text


def test_get_actions_ping_reflects_health(monkeypatch):
    from app import action_runner

    monkeypatch.setattr(actions_router, "ping_crossseed", lambda settings, **_: True)
    client = _client()

    response = client.get("/actions/ping")

    assert response.status_code == 200
    assert "en ligne" in response.text
