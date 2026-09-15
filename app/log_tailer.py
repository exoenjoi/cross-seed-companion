from pathlib import Path

from app.log_parser import ENTRY_RE, LogEntry, parse_log_lines


class LogTailer:
    """Tail un fichier de log accessible via un symlink dont la cible peut changer
    (rotation quotidienne de cross-seed). Ne rejoue jamais le contenu déjà présent
    au premier open — seules les lignes ajoutées ensuite sont retournées."""

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
            self._file = target.open("r")
            if self._first_open:
                self._file.seek(0, 2)  # fin de fichier : le backfill gère déjà l'historique
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
            line = raw_line.rstrip("\n")
            match = ENTRY_RE.match(line)
            if match:
                if self._pending is not None:
                    entries.append(self._pending)
                self._pending = LogEntry(
                    timestamp=match["timestamp"],
                    level=match["level"],
                    component=match["component"],
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
    # ponytail: lit tout le fichier courant (un jour de logs) plutôt que de faire
    # un seek par octets depuis la fin ; à revisiter si un fichier journalier
    # s'avère anormalement gros.
    if not path.exists():
        return []
    lines = path.read_text().splitlines()
    entries = parse_log_lines(lines)
    return entries[-max_entries:]
