from pathlib import Path

from app.crossseed_events import CrossSeedEvent, extract_events
from app.log_paths import CURRENT_LOG_FILENAME
from app.log_parser import parse_log_lines


def list_rotated_log_files(logs_dir: Path) -> list[Path]:
    if not logs_dir.exists():
        return []
    return sorted(p for p in logs_dir.glob("verbose.*.log") if p.name != CURRENT_LOG_FILENAME)


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
