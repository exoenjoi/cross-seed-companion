from dataclasses import dataclass
from pathlib import Path

import yaml

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
    for key in _REQUIRED_FIELDS:
        if key not in raw:
            raise ActionConfigError(f"Action invalide, champ '{key}' manquant : {raw}")
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
    raw = yaml.safe_load(path.read_text())
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
    return actions


def find_action(actions: list[Action], action_id: str) -> Action | None:
    for action in actions:
        if action.id == action_id:
            return action
    return None
