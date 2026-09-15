import httpx

from app.action_runner import ping_crossseed, run_action
from app.actions import Action
from app.config import Settings


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        prowlarr_url="http://prowlarr:9696",
        prowlarr_api_key="prow-key",
        crossseed_url="http://cross-seed:2468",
        crossseed_api_key="cs-key",
        crossseed_config_path="/config",
    )


def test_run_action_sends_request_and_returns_result():
    seen_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        assert request.method == "POST"
        assert str(request.url) == "http://cross-seed:2468/api/job?apikey=cs-key"
        assert request.content == b'{"name":"search"}'
        return httpx.Response(200, text="ok")

    action = Action(
        id="search",
        title="Search",
        method="POST",
        url="${CROSSSEED_URL}/api/job?apikey=${CROSSSEED_API_KEY}",
        body={"name": "search"},
        confirm=None,
        input_label=None,
    )

    result = run_action(action, _settings(), transport=httpx.MockTransport(handler))

    assert len(seen_requests) == 1
    assert result.ok is True
    assert result.status_code == 200
    assert result.body == "ok"


def test_run_action_reports_failure_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    action = Action(
        id="search",
        title="Search",
        method="POST",
        url="${CROSSSEED_URL}/api/job",
        body=None,
        confirm=None,
        input_label=None,
    )

    result = run_action(action, _settings(), transport=httpx.MockTransport(handler))

    assert result.ok is False
    assert result.status_code == 500


def test_run_action_passes_user_input_to_body():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.content == b'{"infoHash":"abc123"}'
        return httpx.Response(200, text="ok")

    action = Action(
        id="notify",
        title="Notify",
        method="POST",
        url="${CROSSSEED_URL}/api/webhook",
        body={"infoHash": "${INPUT}"},
        confirm=None,
        input_label="InfoHash",
    )

    run_action(action, _settings(), user_input="abc123", transport=httpx.MockTransport(handler))


def test_ping_crossseed_returns_true_on_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/ping"
        return httpx.Response(200)

    assert ping_crossseed(_settings(), transport=httpx.MockTransport(handler)) is True


def test_ping_crossseed_returns_false_on_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    assert ping_crossseed(_settings(), transport=httpx.MockTransport(handler)) is False


def test_ping_crossseed_returns_false_on_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    assert ping_crossseed(_settings(), transport=httpx.MockTransport(handler)) is False
