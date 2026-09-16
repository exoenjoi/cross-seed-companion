import json
import re

import httpx
from fastapi import APIRouter, Form, Request

from app.action_runner import ping_crossseed, run_action
from app.actions import ActionConfigError, MissingActionVariableError, find_action, load_all_actions
from app.templates import templates

router = APIRouter()
templates.env.filters["json_compact"] = lambda value: json.dumps(value, ensure_ascii=False)

_API_ENDPOINT_RE = re.compile(r"/api/([^/?]+)")


def _api_endpoint(url: str) -> str:
    match = _API_ENDPOINT_RE.search(url)
    return match.group(1) if match else ""


templates.env.filters["api_endpoint"] = _api_endpoint


@router.get("/actions")
def actions_page(request: Request):
    settings = request.app.state.settings
    try:
        actions = load_all_actions(settings.actions_config_path)
    except ActionConfigError as exc:
        return templates.TemplateResponse(request, "_error_page.html", {"message": str(exc)})
    return templates.TemplateResponse(request, "actions.html", {"actions": actions})


@router.get("/actions/ping")
def actions_ping(request: Request):
    settings = request.app.state.settings
    healthy = ping_crossseed(settings)
    return templates.TemplateResponse(request, "_ping_badge.html", {"healthy": healthy})


@router.post("/actions/{action_id}/run")
def actions_run(request: Request, action_id: str, input: str | None = Form(None)):
    settings = request.app.state.settings
    try:
        actions = load_all_actions(settings.actions_config_path)
    except ActionConfigError as exc:
        return templates.TemplateResponse(request, "_action_result.html", {"ok": False, "message": str(exc)})

    action = find_action(actions, action_id)
    if action is None:
        return templates.TemplateResponse(
            request,
            "_action_result.html",
            {"ok": False, "message": f"Unknown action: {action_id}"},
        )

    try:
        result = run_action(action, settings, user_input=input)
    except (httpx.HTTPError, httpx.InvalidURL, MissingActionVariableError, TypeError) as exc:
        return templates.TemplateResponse(request, "_action_result.html", {"ok": False, "message": str(exc)})

    message = f"{action.title} → HTTP {result.status_code}"
    if not result.ok and result.body:
        message = f"{message}\n{result.body}"
    return templates.TemplateResponse(
        request,
        "_action_result.html",
        {"ok": result.ok, "message": message},
    )
