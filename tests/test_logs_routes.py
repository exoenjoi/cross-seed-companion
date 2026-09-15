import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.log_tailer import LogTailer
from app.routers import logs as logs_router


class _FakeRequest:
    def __init__(self, disconnect_after: int):
        self._count = 0
        self._disconnect_after = disconnect_after

    async def is_disconnected(self) -> bool:
        self._count += 1
        return self._count > self._disconnect_after


def _client(logs_dir) -> TestClient:
    app = FastAPI()
    app.include_router(logs_router.router)
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


def test_get_logs_shows_backfill_entries(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    target = logs_dir / "verbose.2026-09-15.log"
    target.write_text("2026-09-15 00:00:00.000 info: [scheduler] backfilled entry\n")
    (logs_dir / "verbose.current.log").symlink_to(target)

    client = _client(logs_dir)
    response = client.get("/logs")

    assert response.status_code == 200
    assert "backfilled entry" in response.text


def test_get_logs_shows_error_when_logs_missing(tmp_path):
    logs_dir = tmp_path / "logs"  # n'existe pas

    client = _client(logs_dir)
    response = client.get("/logs")

    assert response.status_code == 200
    assert "Erreur" in response.text


def test_format_sse_event_frames_multiline_data():
    result = logs_router.format_sse_event("line1\nline2")

    assert result == "data: line1\ndata: line2\n\n"


def test_sse_log_stream_yields_new_entries_then_stops_on_disconnect(tmp_path):
    target = tmp_path / "verbose.2026-09-15.log"
    target.write_text("")
    current = tmp_path / "verbose.current.log"
    current.symlink_to(target)
    tailer = LogTailer(current)
    tailer.read_new_entries()  # premier open, pointeur en fin de fichier (vide)

    with target.open("a") as f:
        f.write("2026-09-15 00:00:00.000 info: [scheduler] live entry\n")
        f.write("2026-09-15 00:00:01.000 info: [scheduler] closes the previous one\n")

    async def scenario():
        events = []
        request = _FakeRequest(disconnect_after=1)
        async for event in logs_router.sse_log_stream(tailer, request, poll_interval=0.01):
            events.append(event)
        return events

    events = asyncio.run(scenario())

    assert len(events) == 1
    assert "live entry" in events[0]
    assert events[0].startswith("data: ")
    assert events[0].endswith("\n\n")
