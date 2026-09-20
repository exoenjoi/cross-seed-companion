from functools import lru_cache
from pathlib import Path

from app.crossseed_events import MATCH_MARKER, CrossSeedEvent, extract_events
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
    current_path = logs_dir / CURRENT_LOG_FILENAME
    today = current_path.resolve() if current_path.exists() else None
    return sorted(
        (day_label(p) for p in list_rotated_log_files(logs_dir) if p.resolve() != today),
        reverse=True,
    )


def read_log_file(path: Path) -> list[LogEntry]:
    """Every entry of one log file (the current day's via its symlink, or a rotated day's)."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return parse_log_lines(lines)


def read_day_entries(logs_dir: Path, day: str) -> list[LogEntry]:
    path = next((p for p in list_rotated_log_files(logs_dir) if day_label(p) == day), None)
    return read_log_file(path) if path is not None else []


@lru_cache(maxsize=256)
def _file_events(path: Path, mtime_ns: int, size: int) -> tuple[CrossSeedEvent, ...]:
    # mtime_ns/size are cache keys only: rotated logs never change, so only
    # the current day's file is re-parsed when it grows.
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ()
    candidate_lines = [line for line in lines if MATCH_MARKER in line]
    return tuple(extract_events(parse_log_lines(candidate_lines)))


def read_all_events(logs_dir: Path, max_events: int = 500) -> list[CrossSeedEvent]:
    events: list[CrossSeedEvent] = []
    # Newest file first, stopping once we have enough: bounds the amount of
    # log scanned to roughly what's needed, instead of every rotated file
    # the deployment has ever produced.
    for path in reversed(list_rotated_log_files(logs_dir)):
        try:
            stat = path.stat()
        except OSError:
            continue
        events.extend(_file_events(path, stat.st_mtime_ns, stat.st_size))
        if len(events) >= max_events:
            break
    events.sort(key=lambda event: event.timestamp, reverse=True)
    return events[:max_events]
