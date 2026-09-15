from pathlib import Path

import pytest

from app.actions import (
    Action,
    ActionConfigError,
    find_action,
    load_actions_file,
    load_all_actions,
    load_builtin_actions,
)


CUSTOM_YAML = """
- id: my-custom
  title: "Mon action custom"
  method: POST
  url: "${CROSSSEED_URL}/api/job?apikey=${CROSSSEED_API_KEY}"
  body:
    name: search
  confirm: "Confirmer ?"
"""


def test_load_actions_file_parses_full_schema(tmp_path):
    path = tmp_path / "custom.yml"
    path.write_text(CUSTOM_YAML)

    actions = load_actions_file(path)

    assert actions == [
        Action(
            id="my-custom",
            title="Mon action custom",
            method="POST",
            url="${CROSSSEED_URL}/api/job?apikey=${CROSSSEED_API_KEY}",
            body={"name": "search"},
            confirm="Confirmer ?",
            input_label=None,
        )
    ]


def test_load_actions_file_parses_input_label(tmp_path):
    path = tmp_path / "custom.yml"
    path.write_text(
        """
- id: notify
  title: "Notifier"
  method: post
  url: "${CROSSSEED_URL}/api/webhook"
  input_label: "InfoHash"
"""
    )

    actions = load_actions_file(path)

    assert actions[0].method == "POST"  # normalisé en majuscules
    assert actions[0].body is None
    assert actions[0].confirm is None
    assert actions[0].input_label == "InfoHash"


def test_load_actions_file_raises_on_missing_required_field(tmp_path):
    path = tmp_path / "custom.yml"
    path.write_text("- id: incomplete\n  title: \"Sans method ni url\"\n")

    with pytest.raises(ActionConfigError):
        load_actions_file(path)


def test_load_actions_file_raises_when_not_a_list(tmp_path):
    path = tmp_path / "custom.yml"
    path.write_text("id: not-a-list\n")

    with pytest.raises(ActionConfigError):
        load_actions_file(path)


def test_load_builtin_actions_has_six_actions_with_unique_ids():
    actions = load_builtin_actions()

    assert len(actions) == 6
    assert len(set(a.id for a in actions)) == 6


def test_load_all_actions_merges_builtin_and_custom(tmp_path):
    custom_path = tmp_path / "custom.yml"
    custom_path.write_text(CUSTOM_YAML)

    actions = load_all_actions(custom_path)

    assert len(actions) == 7  # 6 builtin + 1 custom
    assert find_action(actions, "my-custom") is not None


def test_load_all_actions_without_custom_path_returns_only_builtin():
    actions = load_all_actions(None)

    assert len(actions) == 6


def test_find_action_returns_none_when_not_found():
    assert find_action([], "missing") is None
