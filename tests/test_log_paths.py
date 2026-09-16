from pathlib import Path

from app.config import Settings
from app.log_paths import CURRENT_LOG_FILENAME, resolve_logs_dir


def _settings(**overrides) -> Settings:
    defaults = dict(
        _env_file=None,
        prowlarr_url="http://prowlarr:9696",
        prowlarr_api_key="prow-key",
        crossseed_url="http://cross-seed:2468",
        crossseed_api_key="cs-key",
        crossseed_config_path="/config",
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_resolve_logs_dir_uses_explicit_path_when_set():
    settings = _settings(crossseed_logs_path="/custom-logs")

    assert resolve_logs_dir(settings) == Path("/custom-logs")


def test_resolve_logs_dir_falls_back_to_config_path_slash_logs():
    settings = _settings(crossseed_config_path="/config")

    assert resolve_logs_dir(settings) == Path("/config/logs")


def test_current_log_filename_constant():
    assert CURRENT_LOG_FILENAME == "verbose.current.log"
