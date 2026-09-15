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


def test_load_actions_file_raises_on_nonexistent_path(tmp_path):
    path = tmp_path / "does-not-exist.yml"

    with pytest.raises(ActionConfigError):
        load_actions_file(path)


def test_load_actions_file_raises_on_non_mapping_list_item(tmp_path):
    path = tmp_path / "custom.yml"
    path.write_text("- \"just a string\"\n")

    with pytest.raises(ActionConfigError):
        load_actions_file(path)


def test_load_actions_file_raises_on_non_string_method(tmp_path):
    path = tmp_path / "custom.yml"
    path.write_text(
        "- id: bad-method\n  title: \"Bad method\"\n  method: 5\n  url: \"http://x\"\n"
    )

    with pytest.raises(ActionConfigError):
        load_actions_file(path)


def test_load_actions_file_raises_on_malformed_yaml(tmp_path):
    path = tmp_path / "custom.yml"
    path.write_text("- id: [unclosed\n")

    with pytest.raises(ActionConfigError):
        load_actions_file(path)


def test_load_all_actions_raises_on_duplicate_id_with_builtin(tmp_path):
    custom_path = tmp_path / "custom.yml"
    custom_path.write_text(
        "- id: search\n  title: \"Fake search\"\n  method: POST\n  url: \"http://x\"\n"
    )

    with pytest.raises(ActionConfigError):
        load_all_actions(custom_path)


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


from app.actions import MissingActionVariableError, render_action
from app.config import Settings


def _settings(**overrides) -> Settings:
    values = {
        "prowlarr_url": "http://prowlarr:9696",
        "prowlarr_api_key": "prow-key",
        "crossseed_url": "http://cross-seed:2468",
        "crossseed_api_key": "cs-key",
        "crossseed_config_path": "/config",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_render_action_substitutes_env_vars_in_url_and_body():
    action = Action(
        id="search",
        title="Search",
        method="POST",
        url="${CROSSSEED_URL}/api/job?apikey=${CROSSSEED_API_KEY}",
        body={"name": "search"},
        confirm=None,
        input_label=None,
    )

    method, url, body = render_action(action, _settings())

    assert method == "POST"
    assert url == "http://cross-seed:2468/api/job?apikey=cs-key"
    assert body == {"name": "search"}


def test_render_action_substitutes_input_placeholder_in_body():
    action = Action(
        id="notify",
        title="Notify",
        method="POST",
        url="${CROSSSEED_URL}/api/webhook",
        body={"infoHash": "${INPUT}"},
        confirm=None,
        input_label="InfoHash",
    )

    _, _, body = render_action(action, _settings(), user_input="abc123")

    assert body == {"infoHash": "abc123"}


def test_render_action_raises_on_unknown_variable():
    action = Action(
        id="bad",
        title="Bad",
        method="GET",
        url="${NOT_A_REAL_VAR}",
        body=None,
        confirm=None,
        input_label=None,
    )

    with pytest.raises(MissingActionVariableError):
        render_action(action, _settings())


def test_render_action_raises_when_input_used_but_not_provided():
    action = Action(
        id="notify",
        title="Notify",
        method="POST",
        url="${CROSSSEED_URL}/api/webhook",
        body={"infoHash": "${INPUT}"},
        confirm=None,
        input_label="InfoHash",
    )

    with pytest.raises(MissingActionVariableError):
        render_action(action, _settings())  # pas de user_input fourni


def test_render_action_leaves_non_string_body_values_untouched():
    action = Action(
        id="search-full",
        title="Search full",
        method="POST",
        url="${CROSSSEED_URL}/api/job",
        body={"name": "search", "ignoreExcludeOlder": True},
        confirm=None,
        input_label=None,
    )

    _, _, body = render_action(action, _settings())

    assert body == {"name": "search", "ignoreExcludeOlder": True}


def test_render_action_raises_on_malformed_placeholder_with_hyphen():
    action = Action(
        id="bad-hyphen",
        title="Bad hyphen",
        method="GET",
        url="${SOME-VAR}",
        body=None,
        confirm=None,
        input_label=None,
    )

    with pytest.raises(MissingActionVariableError):
        render_action(action, _settings())


def test_render_action_raises_on_malformed_placeholder_with_dot():
    action = Action(
        id="bad-dot",
        title="Bad dot",
        method="GET",
        url="${SOME.VAR}",
        body=None,
        confirm=None,
        input_label=None,
    )

    with pytest.raises(MissingActionVariableError):
        render_action(action, _settings())


def test_render_action_raises_on_empty_placeholder():
    action = Action(
        id="bad-empty",
        title="Bad empty",
        method="GET",
        url="prefix ${}",
        body=None,
        confirm=None,
        input_label=None,
    )

    with pytest.raises(MissingActionVariableError):
        render_action(action, _settings())


def test_render_action_substitutes_placeholders_in_nested_dict_body():
    action = Action(
        id="nested-dict",
        title="Nested dict",
        method="POST",
        url="${CROSSSEED_URL}/api/job",
        body={"nested": {"infoHash": "${INPUT}"}},
        confirm=None,
        input_label="InfoHash",
    )

    _, _, body = render_action(action, _settings(), user_input="abc123")

    assert body == {"nested": {"infoHash": "abc123"}}


def test_render_action_substitutes_placeholders_in_list_body():
    action = Action(
        id="list-body",
        title="List body",
        method="POST",
        url="${CROSSSEED_URL}/api/job",
        body={"items": ["${CROSSSEED_API_KEY}", 1], "flag": True},
        confirm=None,
        input_label=None,
    )

    _, _, body = render_action(action, _settings())

    assert body == {"items": ["cs-key", 1], "flag": True}


def test_render_action_raises_on_unknown_placeholder_in_nested_dict():
    action = Action(
        id="nested-unknown",
        title="Nested unknown",
        method="POST",
        url="${CROSSSEED_URL}/api/job",
        body={"nested": {"infoHash": "${UNKNOWN_VAR}"}},
        confirm=None,
        input_label=None,
    )

    with pytest.raises(MissingActionVariableError):
        render_action(action, _settings())


EXAMPLE_ACTIONS_PATH = Path(__file__).resolve().parent.parent / "examples" / "custom-actions.example.yml"


def test_example_custom_actions_file_parses():
    actions = load_actions_file(EXAMPLE_ACTIONS_PATH)

    assert len(actions) >= 1
    assert all(a.method in ("GET", "POST", "PUT", "DELETE", "PATCH") for a in actions)
