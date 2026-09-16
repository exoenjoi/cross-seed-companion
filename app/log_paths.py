from pathlib import Path

from app.config import Settings

CURRENT_LOG_FILENAME = "verbose.current.log"


def resolve_logs_dir(settings: Settings) -> Path:
    return Path(settings.crossseed_logs_path or (settings.crossseed_config_path / "logs"))
