from pathlib import Path

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.templating import Jinja2Templates

from app.action_runner import ping_crossseed, run_action
from app.actions import ActionConfigError, MissingActionVariableError, find_action, load_all_actions

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


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
            {"ok": False, "message": f"Action inconnue : {action_id}"},
        )

    try:
        result = run_action(action, settings, user_input=input)
    except (httpx.HTTPError, MissingActionVariableError) as exc:
        return templates.TemplateResponse(request, "_action_result.html", {"ok": False, "message": str(exc)})

    message = f"{action.title} → HTTP {result.status_code}"
    if not result.ok and result.body:
        message = f"{message}\n{result.body}"
    return templates.TemplateResponse(
        request,
        "_action_result.html",
        {"ok": result.ok, "message": message},
    )
