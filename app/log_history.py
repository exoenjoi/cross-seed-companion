from pathlib import Path

from app.crossseed_events import CrossSeedEvent, extract_events
from app.log_paths import CURRENT_LOG_FILENAME
from app.log_parser import LogEntry, parse_log_lines


def list_rotated_log_files(logs_dir: Path) -> list[Path]:
    if not logs_dir.exists():
        return []
    return sorted(p for p in logs_dir.glob("verbose.*.log") if p.name != CURRENT_LOG_FILENAME)


def day_label(path: Path) -> str:
    return path.name.removeprefix("verbose.").removesuffix(".log")


def list_available_days(logs_dir: Path) -> list[str]:
    """Available days (excluding the current day), newest to oldest."""
    return sorted((day_label(p) for p in list_rotated_log_files(logs_dir)), reverse=True)


def read_day_entries(logs_dir: Path, day: str) -> list[LogEntry]:
    path = next((p for p in list_rotated_log_files(logs_dir) if day_label(p) == day), None)
    if path is None:
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return parse_log_lines(lines)


def read_all_events(logs_dir: Path, max_events: int = 500) -> list[CrossSeedEvent]:
    events: list[CrossSeedEvent] = []
    for path in list_rotated_log_files(logs_dir):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        entries = parse_log_lines(lines)
        events.extend(extract_events(entries))
    events.sort(key=lambda event: event.timestamp, reverse=True)
    return events[:max_events]
