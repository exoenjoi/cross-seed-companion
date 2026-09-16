import re
from dataclasses import dataclass

from app.log_parser import LogEntry

MATCH_RE = re.compile(
    r"^Found (?P<name>.+?) \[[0-9a-fA-F]+\.\.\.\] on (?P<tracker>.+?) "
    r"by MATCH from torrentClient \(.+?\) - (?P<outcome>.+)$"
)

# Only these two outcomes are genuine successful additions — verified against
# a real ~15-day log corpus. Every other outcome ("failed to inject,
# saving...", "exists", "source is incomplete, saving...", or anything
# unrecognized) is an attempt or a no-op, not a new addition. See the spec's
# 2026-09-16 addendum for the full corpus breakdown.
SUCCESSFUL_OUTCOMES = frozenset({"injected", "saved"})


@dataclass
class CrossSeedEvent:
    timestamp: str
    name: str
    tracker: str
    outcome: str
    component: str


def extract_events(entries: list[LogEntry]) -> list[CrossSeedEvent]:
    events: list[CrossSeedEvent] = []
    for entry in entries:
        match = MATCH_RE.match(entry.message)
        if match and match["outcome"] in SUCCESSFUL_OUTCOMES:
            events.append(
                CrossSeedEvent(
                    timestamp=entry.timestamp,
                    name=match["name"],
                    tracker=match["tracker"],
                    outcome=match["outcome"],
                    component=entry.component,
                )
            )
    return events
