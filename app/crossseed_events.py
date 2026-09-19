import re
from dataclasses import dataclass

from app.log_parser import LogEntry

MATCH_RE = re.compile(
    r"^Found (?P<name>.+?) \[[0-9a-fA-F]+\.\.\.\] on (?P<tracker>.+?) "
    r"by (?:MATCH|MATCH_SIZE_ONLY) from \w+ \(.+?\) - (?P<outcome>.+)$"
)

# Any line MATCH_RE can possibly match contains this substring — used to
# cheaply skip the vast majority of (irrelevant) log lines before the more
# expensive per-line parsing in log_history.read_all_events.
MATCH_MARKER = " by MATCH"

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


@dataclass
class GroupedEvent:
    name: str
    timestamp: str
    outcome: str
    trackers: list[str]


def extract_events(entries: list[LogEntry]) -> list[CrossSeedEvent]:
    events: list[CrossSeedEvent] = []
    for entry in entries:
        message = entry.message.partition("\n")[0][:1024]
        match = MATCH_RE.match(message)
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


def group_events_by_name(events: list[CrossSeedEvent]) -> list[GroupedEvent]:
    """Merge same-torrent events (one per indexer it was cross-seeded to)
    into a single row. `events` must already be newest-first: the first
    occurrence of a name sets the group's displayed timestamp/outcome."""
    groups: dict[str, GroupedEvent] = {}
    order: list[str] = []
    for event in events:
        group = groups.get(event.name)
        if group is None:
            group = GroupedEvent(
                name=event.name,
                timestamp=event.timestamp,
                outcome=event.outcome,
                trackers=[event.tracker],
            )
            groups[event.name] = group
            order.append(event.name)
        elif event.tracker not in group.trackers:
            group.trackers.append(event.tracker)
    return [groups[name] for name in order]
