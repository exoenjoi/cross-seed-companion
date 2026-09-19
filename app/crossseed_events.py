import re
from dataclasses import dataclass

from app.log_parser import LogEntry

# "Found <name> [<hash>...] on <tracker> by <decision> from <kind> (<source> [<hash>...@<client>]) - <outcome>"
# The first hash is the torrent cross-seed created (unique per injection); the
# second one is the torrent it was made from (empty for "virtual" season-pack sources).
MATCH_RE = re.compile(
    r"^Found (?P<name>.+?) \[(?P<candidate_hash>[0-9a-fA-F]+)\.\.\.\] on (?P<tracker>.+?) "
    r"by (?:MATCH|MATCH_SIZE_ONLY) from \w+ \((?P<source_name>.+?)"
    r"(?: \[(?P<source_hash>[0-9a-fA-F]*)(?:\.\.\.)?@[^\]]*\])?\) - (?P<outcome>.+)$"
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
    candidate_hash: str = ""
    source_name: str = ""
    source_hash: str = ""


@dataclass
class Injection:
    tracker: str
    timestamp: str
    outcome: str


@dataclass
class DayEntry:
    tracker: str
    time: str  # HH:MM
    outcome: str
    count: int = 1  # identical injections (same tracker, minute and outcome) shown once


@dataclass
class DayGroup:
    day: str  # YYYY-MM-DD
    entries: list[DayEntry]


@dataclass
class GroupedEvent:
    """One torrent (a family of cross-seeded copies) and every injection made for it."""

    name: str
    timestamp: str  # latest injection
    injections: list[Injection]  # newest first

    @property
    def days(self) -> list[DayGroup]:
        days: list[DayGroup] = []
        for injection in self.injections:
            day, time = injection.timestamp[:10], injection.timestamp[11:16]
            if not days or days[-1].day != day:
                days.append(DayGroup(day, []))
            entries = days[-1].entries
            for entry in entries:
                if (entry.tracker, entry.time, entry.outcome) == (injection.tracker, time, injection.outcome):
                    entry.count += 1
                    break
            else:
                entries.append(DayEntry(injection.tracker, time, injection.outcome))
        return days


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
                    candidate_hash=match["candidate_hash"].lower(),
                    source_name=match["source_name"],
                    source_hash=(match["source_hash"] or "").lower(),
                )
            )
    return events


def group_events(events: list[CrossSeedEvent]) -> list[GroupedEvent]:
    """Group injections of the same torrent, whatever their names or dates.

    A torrent's identity is its lineage, not its name: every copy cross-seed
    creates is linked to the torrent it was made from (candidate hash -> source
    hash), and copies can themselves be the source of later ones. Chained
    links form a family; each family is one row. `events` must be newest-first.
    """
    parent: dict[str, str] = {}

    def find(h: str) -> str:
        parent.setdefault(h, h)
        while parent[h] != h:
            parent[h] = parent[parent[h]]
            h = parent[h]
        return h

    for event in events:
        if event.source_hash:
            parent[find(event.candidate_hash)] = find(event.source_hash)

    families: dict[str, list[CrossSeedEvent]] = {}
    for event in events:
        families.setdefault(find(event.candidate_hash), []).append(event)

    groups = []
    for members in families.values():
        oldest = members[-1]
        groups.append(
            GroupedEvent(
                # A copy of another torrent is named after its original (the
                # oldest source we know of); a "virtual" source has no torrent of its own.
                name=oldest.source_name if oldest.source_hash else oldest.name,
                timestamp=members[0].timestamp,
                injections=[Injection(e.tracker, e.timestamp, e.outcome) for e in members],
            )
        )
    return groups
