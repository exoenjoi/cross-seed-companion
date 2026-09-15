import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.config import Settings

BUILTIN_ACTIONS_PATH = Path(__file__).resolve().parent / "actions_builtin.yaml"


class ActionConfigError(Exception):
    """Levée quand un fichier d'actions YAML est malformé."""


@dataclass
class Action:
    id: str
    title: str
    method: str
    url: str
    body: dict | None
    confirm: str | None
    input_label: str | None


_REQUIRED_FIELDS = ("id", "title", "method", "url")


def _parse_action(raw: dict) -> Action:
    if not isinstance(raw, dict):
        raise ActionConfigError(f"Action invalide, mapping YAML attendu : {raw!r}")
    for key in _REQUIRED_FIELDS:
        if key not in raw:
            raise ActionConfigError(f"Action invalide, champ '{key}' manquant : {raw}")
    if not isinstance(raw["method"], str):
        raise ActionConfigError(f"Action '{raw['id']}' : le champ 'method' doit être une chaîne.")
    return Action(
        id=raw["id"],
        title=raw["title"],
        method=raw["method"].upper(),
        url=raw["url"],
        body=raw.get("body"),
        confirm=raw.get("confirm"),
        input_label=raw.get("input_label"),
    )


def load_actions_file(path: Path) -> list[Action]:
    try:
        text = path.read_text()
    except OSError as exc:
        raise ActionConfigError(f"Fichier d'actions illisible : {path} ({exc})") from exc
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ActionConfigError(f"YAML invalide dans {path} : {exc}") from exc
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise ActionConfigError(f"{path} doit contenir une liste YAML d'actions.")
    return [_parse_action(item) for item in raw]


def load_builtin_actions() -> list[Action]:
    return load_actions_file(BUILTIN_ACTIONS_PATH)


def load_all_actions(custom_path: Path | None) -> list[Action]:
    actions = load_builtin_actions()
    if custom_path is not None:
        actions = actions + load_actions_file(custom_path)
    seen: set[str] = set()
    for action in actions:
        if action.id in seen:
            raise ActionConfigError(f"Action en double : l'id '{action.id}' est utilisé plusieurs fois.")
        seen.add(action.id)
    return actions


def find_action(actions: list[Action], action_id: str) -> Action | None:
    for action in actions:
        if action.id == action_id:
            return action
    return None


_VAR_RE = re.compile(r"\$\{([^}]*)\}")


class MissingActionVariableError(Exception):
    """Levée quand une action référence une variable ${...} inconnue ou un ${INPUT} non fourni."""


def _available_variables(settings: Settings, user_input: str | None) -> dict[str, str]:
    variables = {
        "CROSSSEED_URL": settings.crossseed_url,
        "CROSSSEED_API_KEY": settings.crossseed_api_key,
        "PROWLARR_URL": settings.prowlarr_url,
        "PROWLARR_API_KEY": settings.prowlarr_api_key,
    }
    if user_input is not None:
        variables["INPUT"] = user_input
    return variables


def _substitute(text: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name not in variables:
            raise MissingActionVariableError(
                f"Variable inconnue ou non fournie dans une action : ${{{name}}}"
            )
        return variables[name]

    return _VAR_RE.sub(replace, text)


def _substitute_value(value, variables: dict[str, str]):
    """Recursively substitute placeholders in strings, dicts, lists, and tuples."""
    if isinstance(value, str):
        return _substitute(value, variables)
    elif isinstance(value, dict):
        return {k: _substitute_value(v, variables) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        result = [_substitute_value(item, variables) for item in value]
        return result if isinstance(value, list) else tuple(result)
    else:
        # bool, int, None, etc. are returned unchanged
        return value


def render_action(
    action: Action,
    settings: Settings,
    user_input: str | None = None,
) -> tuple[str, str, dict | None]:
    variables = _available_variables(settings, user_input)
    url = _substitute(action.url, variables)
    body = None
    if action.body is not None:
        body = _substitute_value(action.body, variables)
    return action.method, url, body
