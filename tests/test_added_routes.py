from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.routers import added as added_router


def _client(logs_dir) -> TestClient:
    app = FastAPI()
    app.include_router(added_router.router)
    app.state.settings = Settings(
        _env_file=None,
        prowlarr_url="http://prowlarr:9696",
        prowlarr_api_key="prow-key",
        crossseed_url="http://cross-seed:2468",
        crossseed_api_key="cs-key",
        crossseed_config_path="/config",
        crossseed_logs_path=str(logs_dir),
    )
    return TestClient(app)


def test_get_added_shows_events_from_rotated_files(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    day1 = logs_dir / "verbose.2026-09-14.log"
    day1.write_text(
        "2026-09-14 10:00:00.000 info: [rss] Found Movie.One.mkv [aaaaaaaa...] on TrackerA "
        "by MATCH from torrentClient (Movie.One.mkv [bbbbbbbb...@client]) - injected\n"
    )

    client = _client(logs_dir)
    response = client.get("/added")

    assert response.status_code == 200
    assert "Movie.One.mkv" in response.text
    assert "TrackerA" in response.text
    assert "1 torrent(s) added" in response.text


def test_get_added_groups_same_torrent_across_trackers(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    day1 = logs_dir / "verbose.2026-09-14.log"
    lines = [
        f"2026-09-14 10:00:00.000 info: [rss] Found Movie.One.mkv [aaaaaaaa...] on {tracker} "
        "by MATCH from torrentClient (Movie.One.mkv [bbbbbbbb...@client]) - injected\n"
        for tracker in ("TrackerA", "TrackerB")
    ]
    day1.write_text("".join(lines))

    client = _client(logs_dir)
    response = client.get("/added")

    assert response.status_code == 200
    assert "1 torrent(s) added" in response.text
    assert "TrackerA, TrackerB" in response.text


def test_get_added_shows_empty_state_when_no_events(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    client = _client(logs_dir)
    response = client.get("/added")

    assert response.status_code == 200
    assert "No additions" in response.text


def test_get_added_shows_error_when_logs_missing(tmp_path):
    logs_dir = tmp_path / "logs"  # does not exist

    client = _client(logs_dir)
    response = client.get("/added")

    assert response.status_code == 200
    assert "Error" in response.text


def test_get_added_refresh_returns_partial_without_page_shell(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    day1 = logs_dir / "verbose.2026-09-14.log"
    day1.write_text(
        "2026-09-14 10:00:00.000 info: [rss] Found Movie.One.mkv [aaaaaaaa...] on TrackerA "
        "by MATCH from torrentClient (Movie.One.mkv [bbbbbbbb...@client]) - injected\n"
    )

    client = _client(logs_dir)
    response = client.get("/added/refresh")

    assert response.status_code == 200
    assert "Movie.One.mkv" in response.text
    assert "Cross-Seed Companion" not in response.text


def test_get_added_refresh_shows_error_when_logs_missing(tmp_path):
    logs_dir = tmp_path / "logs"  # does not exist

    client = _client(logs_dir)
    response = client.get("/added/refresh")

    assert response.status_code == 200
    assert "Error" in response.text
