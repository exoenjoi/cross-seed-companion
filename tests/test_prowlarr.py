import httpx

from app.prowlarr import ProwlarrClient


INDEXERS_JSON = [
    {"id": 1, "name": "The Old School", "enable": True, "privacy": "private", "tags": []},
    {"id": 2, "name": "PublicTracker", "enable": True, "privacy": "public", "tags": []},
    {"id": 3, "name": "Disabled", "enable": False, "privacy": "private", "tags": []},
]

TAGS_JSON = [
    {"id": 10, "label": "no-cross-seed"},
    {"id": 11, "label": "anime"},
]


def _make_client(handler) -> ProwlarrClient:
    return ProwlarrClient(
        base_url="http://prowlarr:9696",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )


def test_get_indexers_parses_response_and_sends_api_key_header():
    seen_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        assert request.url.path == "/api/v1/indexer"
        assert request.headers["X-Api-Key"] == "test-key"
        return httpx.Response(200, json=INDEXERS_JSON)

    client = _make_client(handler)
    indexers = client.get_indexers()

    assert len(seen_requests) == 1
    assert [i.id for i in indexers] == [1, 2, 3]
    assert indexers[0].privacy == "private"
    assert indexers[1].privacy == "public"
    assert indexers[2].enable is False


def test_get_tags_parses_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/tag"
        return httpx.Response(200, json=TAGS_JSON)

    client = _make_client(handler)
    tags = client.get_tags()

    assert [(t.id, t.label) for t in tags] == [(10, "no-cross-seed"), (11, "anime")]


def test_get_indexers_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = _make_client(handler)
    try:
        client.get_indexers()
        assert False, "expected httpx.HTTPStatusError"
    except httpx.HTTPStatusError:
        pass
