import re
from dataclasses import dataclass

ENTRY_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) "
    r"(?P<level>\w+): \[(?P<component>[^\]]*)\] (?P<message>.*)$"
)


@dataclass
class LogEntry:
    timestamp: str
    level: str
    component: str
    message: str


def parse_log_lines(lines: list[str]) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for line in lines:
        match = ENTRY_RE.match(line)
        if match:
            entries.append(
                LogEntry(
                    timestamp=match["timestamp"],
                    level=match["level"],
                    component=match["component"],
                    message=match["message"],
                )
            )
        elif entries:
            entries[-1].message += "\n" + line
    return entries
