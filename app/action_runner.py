import json
from dataclasses import dataclass

import httpx

from app.actions import Action, render_action
from app.config import Settings


@dataclass
class ActionResult:
    ok: bool
    status_code: int
    body: str


def run_action(
    action: Action,
    settings: Settings,
    user_input: str | None = None,
    transport: httpx.BaseTransport | None = None,
) -> ActionResult:
    method, url, body = render_action(action, settings, user_input)
    with httpx.Client(transport=transport, timeout=15.0) as client:
        if body is not None:
            content = json.dumps(body, separators=(',', ':'))
            response = client.request(method, url, content=content, headers={"content-type": "application/json"})
        else:
            response = client.request(method, url)
    return ActionResult(ok=response.is_success, status_code=response.status_code, body=response.text)


def ping_crossseed(settings: Settings, transport: httpx.BaseTransport | None = None) -> bool:
    url = f"{settings.crossseed_url.rstrip('/')}/api/ping"
    try:
        with httpx.Client(transport=transport, timeout=5.0) as client:
            response = client.get(url)
        return response.is_success
    except httpx.HTTPError:
        return False
