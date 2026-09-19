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
    assert "Run a search" in response.text
    assert "Search a torrent by infoHash" in response.text
    assert "Update indexer capabilities" in response.text


def test_get_actions_shows_error_when_custom_file_invalid(tmp_path):
    bad_file = tmp_path / "custom.yml"
    bad_file.write_text("id: not-a-list\n")
    client = _client(actions_config_path=str(bad_file))

    response = client.get("/actions")

    assert response.status_code == 200
    assert "Error" in response.text


def test_get_actions_shows_error_when_custom_file_missing(tmp_path):
    missing_file = tmp_path / "does-not-exist.yml"
    client = _client(actions_config_path=str(missing_file))

    response = client.get("/actions")

    assert response.status_code == 200
    assert "Error" in response.text


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
    assert "Error" in response.text
    assert "does-not-exist" in response.text


def test_post_run_action_handles_non_httperror_exception(monkeypatch):
    """A malformed custom action (e.g. a bare YAML date in the body, which
    json.dumps can't serialize) must render an error fragment, not a 500."""

    def fake_run_action(action, settings, user_input=None, transport=None):
        raise TypeError("Object of type date is not JSON serializable")

    monkeypatch.setattr(actions_router, "run_action", fake_run_action)
    client = _client()

    response = client.post("/actions/search/run")

    assert response.status_code == 200
    assert "Error" in response.text
    assert "not JSON serializable" in response.text


def test_get_actions_ping_reflects_health(monkeypatch):
    from app import action_runner

    monkeypatch.setattr(actions_router, "ping_crossseed", lambda settings, **_: True)
    client = _client()

    response = client.get("/actions/ping")

    assert response.status_code == 200
    assert "online" in response.text


def test_post_run_action_shows_custom_message_for_a_documented_status(monkeypatch):
    from app import action_runner

    def fake_run_action(action, settings, user_input=None, transport=None):
        return action_runner.ActionResult(ok=False, status_code=409, body='{"raw":"noise"}')

    monkeypatch.setattr(actions_router, "run_action", fake_run_action)
    client = _client()

    response = client.post("/actions/search/run")

    assert "HTTP 409" in response.text
    assert "already running" in response.text.lower()
    assert "noise" not in response.text


def test_post_run_action_keeps_raw_body_for_undocumented_failure(monkeypatch):
    from app import action_runner

    def fake_run_action(action, settings, user_input=None, transport=None):
        return action_runner.ActionResult(ok=False, status_code=500, body="boom")

    monkeypatch.setattr(actions_router, "run_action", fake_run_action)
    client = _client()

    response = client.post("/actions/search/run")

    assert "HTTP 500" in response.text
    assert "boom" in response.text
