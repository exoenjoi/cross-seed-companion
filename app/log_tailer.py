from pathlib import Path

from app.log_parser import ENTRY_RE, LogEntry, parse_log_lines


class LogTailer:
    """Tails a log file accessed via a symlink whose target can change
    (cross-seed's daily rotation). Never replays content already present
    at first open — only lines appended afterward are returned."""

    def __init__(self, symlink_path: Path) -> None:
        self._symlink_path = symlink_path
        self._file = None
        self._target: Path | None = None
        self._pending: LogEntry | None = None
        self._first_open = True

    def _reopen_if_rotated(self) -> bool:
        target = self._symlink_path.resolve()
        if target == self._target:
            return False
        if self._file is not None:
            self._file.close()
            self._file = None
        if target.exists():
            self._file = target.open("r", encoding="utf-8", errors="replace")
            if self._first_open:
                self._file.seek(0, 2)  # end of file: backfill already covers the history
            self._target = target
            self._first_open = False
        return True

    def read_new_entries(self) -> list[LogEntry]:
        entries: list[LogEntry] = []
        rotated = self._reopen_if_rotated()
        if rotated and self._pending is not None:
            entries.append(self._pending)
            self._pending = None
        if self._file is None:
            return entries
        for raw_line in self._file.readlines():
            line = raw_line.rstrip("\r\n")
            match = ENTRY_RE.match(line)
            if match:
                if self._pending is not None:
                    entries.append(self._pending)
                self._pending = LogEntry(
                    timestamp=match["timestamp"],
                    level=match["level"],
                    component=match["component"] or "",
                    message=match["message"],
                )
            elif self._pending is not None:
                self._pending.message += "\n" + line
        return entries

    def close(self) -> None:
        """Close the underlying file handle if open."""
        if self._file is not None:
            self._file.close()
            self._file = None


def read_recent_entries(path: Path, max_entries: int = 200) -> list[LogEntry]:
    # ponytail: reads the whole current file (one day of logs) instead of
    # byte-seeking from the end; revisit if a daily file turns out to be
    # unusually large.
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    entries = parse_log_lines(lines)
    return entries[-max_entries:]
