import time
from datetime import date

from app.crossseed_events import (
    AddedStats,
    CrossSeedEvent,
    DayEntry,
    DayGroup,
    Injection,
    extract_events,
    group_events,
    summarize,
)
from app.log_parser import LogEntry


def test_extract_events_matches_successful_injected_line():
    entry = LogEntry(
        timestamp="2026-09-11 11:26:46.414",
        level="info",
        component="rss",
        message=(
            "Found Some.Movie.2025.2160p.WEBRip.x265-GROUP.mkv [c0ffee01...] on TrackerE "
            "by MATCH from torrentClient (Some.Movie.2025.2160p.WEBRip.x265-GROUP.mkv "
            "[c0ffee02...@192.0.2.10:8090]) - injected"
        ),
    )

    events = extract_events([entry])

    assert events == [
        CrossSeedEvent(
            timestamp="2026-09-11 11:26:46.414",
            name="Some.Movie.2025.2160p.WEBRip.x265-GROUP.mkv",
            tracker="TrackerE",
            outcome="injected",
            component="rss",
            candidate_hash="c0ffee01",
            source_name="Some.Movie.2025.2160p.WEBRip.x265-GROUP.mkv",
            source_hash="c0ffee02",
        )
    ]


def test_extract_events_matches_saved_outcome():
    entry = LogEntry(
        timestamp="2026-09-11 12:00:00.000",
        level="info",
        component="search",
        message=(
            "Found Some.Show.S01E01.1080p.mkv [aaaaaaaa...] on TrackerY "
            "by MATCH from torrentClient (Some.Show.S01E01.1080p.mkv [bbbbbbbb...@client]) - saved"
        ),
    )

    events = extract_events([entry])

    assert events[0].outcome == "saved"


def test_extract_events_handles_name_with_parentheses_and_tracker_with_api_suffix():
    entry = LogEntry(
        timestamp="2026-09-07 08:35:26.248",
        level="info",
        component="rss",
        message=(
            "Found Other Movie (2015) MULTi 2160p BluRay x265-GROUP.mkv "
            "[c0ffee03...] on Tracker Name (API) by MATCH from torrentClient "
            "(Other Movie (2015) MULTi 2160p BluRay x265-GROUP.mkv "
            "[c0ffee04...@192.0.2.10:8090]) - injected"
        ),
    )

    events = extract_events([entry])

    assert events[0].name == "Other Movie (2015) MULTi 2160p BluRay x265-GROUP.mkv"
    assert events[0].tracker == "Tracker Name (API)"


def test_extract_events_excludes_failed_injection_outcome():
    # Real-world example: a chronic client-side injection failure. Per the
    # spec's 2026-09-16 addendum, "failed to inject, saving..." is NOT a
    # successful addition even though the line otherwise matches the MATCH
    # pattern.
    entry = LogEntry(
        timestamp="2026-09-02 00:16:21.400",
        level="error",
        component="inject",
        message=(
            "Found Old.Movie.1999.1080p.BluRay.x264-GROUP.mkv [c0ffee05...] on TrackerD "
            "by MATCH from torrentClient (Old.Movie.1999.1080p.BluRay.x264-GROUP.mkv "
            "[c0ffee06...@192.0.2.10:8090]) - failed to inject, saving..."
        ),
    )

    assert extract_events([entry]) == []


def test_extract_events_excludes_already_exists_outcome():
    entry = LogEntry(
        timestamp="2026-09-13 08:08:08.939",
        level="verbose",
        component="inject",
        message=(
            "Found Some.Show.S12E04.1080p.mkv [c0ffee07...] on TrackerD "
            "by MATCH from torrentClient (Some.Show.S12E04.1080p.mkv "
            "[c0ffee08...@192.0.2.10:8090]) - exists"
        ),
    )

    assert extract_events([entry]) == []


def test_extract_events_ignores_inject_linking_lines():
    entry = LogEntry(
        timestamp="2026-09-02 00:15:28.689",
        level="verbose",
        component="inject",
        message="Linking Some.Movie.2024.1080p.mkv [c0ffee09...] from Some.Movie.2024.1080p.mkv [c0ffee0a...@client] to /downloads/complete",
    )

    assert extract_events([entry]) == []


def test_extract_events_ignores_injection_failed_error_lines():
    entry = LogEntry(
        timestamp="2026-09-02 00:15:54.924",
        level="error",
        component="qbittorrent@192.0.2.10:8090",
        message="Injection failed for Some.Movie.2024.1080p.mkv [c0ffee09...]: Failed to retrieve torrent after adding",
    )

    assert extract_events([entry]) == []


def test_extract_events_ignores_bracket_less_lines():
    entry = LogEntry(
        timestamp="2026-09-02 00:15:54.930",
        level="verbose",
        component="",
        message="Unlinking /data/torrents/completed/Some.Movie.2024.1080p.mkv",
    )

    assert extract_events([entry]) == []


def test_extract_events_matches_line_with_trailing_continuation_line():
    # A successful match line that picked up a JS-stack-trace continuation
    # line (log_parser.py appends it with "\n"). Because MATCH_RE's "."
    # doesn't cross newlines, matching the full multi-line message would
    # silently drop this event — extract_events must match only the first
    # line and still find it.
    entry = LogEntry(
        timestamp="2026-09-11 11:26:46.414",
        level="info",
        component="rss",
        message=(
            "Found Some.Movie.2025.2160p.WEBRip.x265-GROUP.mkv [c0ffee01...] on TrackerE "
            "by MATCH from torrentClient (Some.Movie.2025.2160p.WEBRip.x265-GROUP.mkv "
            "[c0ffee02...@192.0.2.10:8090]) - injected"
            "\n    at Object.<anonymous> (/app/x.js:1:1)"
        ),
    )

    events = extract_events([entry])

    assert events == [
        CrossSeedEvent(
            timestamp="2026-09-11 11:26:46.414",
            name="Some.Movie.2025.2160p.WEBRip.x265-GROUP.mkv",
            tracker="TrackerE",
            outcome="injected",
            component="rss",
            candidate_hash="c0ffee01",
            source_name="Some.Movie.2025.2160p.WEBRip.x265-GROUP.mkv",
            source_hash="c0ffee02",
        )
    ]


def test_extract_events_bounds_backtracking_on_adversarial_non_matching_line():
    # A long line that starts with "Found " but never completes the match
    # (no trailing " - <outcome>") used to cause catastrophic backtracking
    # in MATCH_RE's nested non-greedy groups. The 1024-byte cap keeps this
    # fast and deterministic regardless of line length.
    entry = LogEntry(
        timestamp="2026-09-11 11:26:46.414",
        level="info",
        component="rss",
        message="Found " + "X [aaaaaaaa...] on Y by MATCH from torrentClient (z) " * 400,
    )

    start = time.monotonic()
    events = extract_events([entry])
    elapsed = time.monotonic() - start

    assert events == []
    assert elapsed < 1.0


def test_extract_events_returns_empty_list_for_no_entries():
    assert extract_events([]) == []


def test_extract_events_reads_candidate_and_source_identity():
    entry = LogEntry(
        timestamp="2026-09-19 18:44:33.674",
        level="info",
        component="search",
        message=(
            "Found Example Movie (2024) Hybrid MULTi.mkv [d00d0001...] on TrackerD "
            "by MATCH_SIZE_ONLY from torrentClient (Example Movie (2024) [d00d0002...@192.0.2.10:8090]) - injected"
        ),
    )

    event = extract_events([entry])[0]

    assert (event.candidate_hash, event.source_name, event.source_hash) == (
        "d00d0001",
        "Example Movie (2024)",
        "d00d0002",
    )


def test_extract_events_handles_virtual_source_without_hash():
    entry = LogEntry(
        timestamp="2026-09-13 08:07:50.718",
        level="info",
        component="search",
        message=(
            "Found Kids.Show.S12E04.mkv [c0ffee07...] on TrackerD by MATCH from virtual "
            "(Kids.Show.S12.1080p-GROUP [@192.0.2.10:8090]) - injected"
        ),
    )

    event = extract_events([entry])[0]

    assert event.candidate_hash == "c0ffee07"
    assert event.source_hash == ""
    assert event.source_name == "Kids.Show.S12.1080p-GROUP"


def _event(ts, tracker, candidate, source, name="X", source_name="X", outcome="injected"):
    return CrossSeedEvent(ts, name, tracker, outcome, "search", candidate, source_name, source)


# Example Movie (2024) history modelled on real logs: the TrackerF copy (d00d0002) later
# served as the source for TrackerG and TrackerD, all from original d00d0004.
LINEAGE = [
    _event("2026-09-19 18:44:33.674", "TrackerD", "d00d0001", "d00d0002", "Example Movie (2024) Hybrid MULTi.mkv", "Example Movie (2024)"),
    _event("2026-09-19 18:44:32.829", "TrackerG (API)", "d00d0003", "d00d0002", "Example Movie (2024) Hybrid MULTi.mkv", "Example Movie (2024)"),
    _event("2026-09-19 17:31:55.662", "TrackerF", "d00d0002", "d00d0004", "Example Movie (2024)", "Example Movie (2024) Hybrid MULTi.mkv"),
    _event("2026-09-05 13:31:04.328", "TrackerE", "d00d0005", "d00d0004", "Example Movie (2024) Hybrid MULTi.mkv", "Example Movie (2024) Hybrid MULTi.mkv"),
]


def test_group_events_links_copies_through_their_source_chain():
    groups = group_events(LINEAGE)

    assert len(groups) == 1
    lineage = groups[0]
    assert lineage.name == "Example Movie (2024) Hybrid MULTi.mkv"  # the original torrent's name
    assert lineage.timestamp == "2026-09-19 18:44:33.674"
    assert lineage.injections == [
        Injection("TrackerD", "2026-09-19 18:44:33.674", "injected"),
        Injection("TrackerG (API)", "2026-09-19 18:44:32.829", "injected"),
        Injection("TrackerF", "2026-09-19 17:31:55.662", "injected"),
        Injection("TrackerE", "2026-09-05 13:31:04.328", "injected"),
    ]


def test_group_events_keeps_each_injection_date_separate():
    injection = next(i for i in group_events(LINEAGE)[0].injections if i.tracker == "TrackerE")

    assert injection.timestamp == "2026-09-05 13:31:04.328"


def test_group_events_does_not_merge_unrelated_torrents_sharing_a_name():
    events = [
        _event("2026-09-14 10:00:00.000", "TrackerA", "aaaaaaaa", "11111111", "Same.Name.mkv", "Original One.mkv"),
        _event("2026-09-13 10:00:00.000", "TrackerB", "bbbbbbbb", "22222222", "Same.Name.mkv", "Original Two.mkv"),
    ]

    groups = group_events(events)

    assert [g.name for g in groups] == ["Original One.mkv", "Original Two.mkv"]


def test_group_events_treats_virtual_sources_as_separate_torrents():
    events = [
        _event("2026-09-13 08:07:51.120", "TrackerD", "d00d0006", "", "Kids.Show.S12E08.mkv", "Kids.Show.S12.1080p-pack"),
        _event("2026-09-13 08:07:50.718", "TrackerD", "c0ffee07", "", "Kids.Show.S12E04.mkv", "Kids.Show.S12.1080p-pack"),
    ]

    groups = group_events(events)

    assert [g.name for g in groups] == ["Kids.Show.S12E08.mkv", "Kids.Show.S12E04.mkv"]


def test_group_events_orders_torrents_by_their_latest_injection():
    events = [
        _event("2026-09-19 10:00:00.000", "TrackerA", "aaaaaaaa", "11111111", source_name="One"),
        _event("2026-09-18 10:00:00.000", "TrackerB", "bbbbbbbb", "22222222", source_name="Two"),
        _event("2026-09-17 10:00:00.000", "TrackerC", "cccccccc", "11111111", source_name="One"),
    ]

    groups = group_events(events)

    assert [g.name for g in groups] == ["One", "Two"]
    assert [i.tracker for i in groups[0].injections] == ["TrackerA", "TrackerC"]


def test_group_events_returns_empty_list_for_no_events():
    assert group_events([]) == []


def test_days_groups_a_torrents_injections_by_day_newest_first():
    days = group_events(LINEAGE)[0].days

    assert days == [
        DayGroup(
            "2026-09-19",
            [
                DayEntry("TrackerD", "18:44", "injected"),
                DayEntry("TrackerG (API)", "18:44", "injected"),
                DayEntry("TrackerF", "17:31", "injected"),
            ],
        ),
        DayGroup("2026-09-05", [DayEntry("TrackerE", "13:31", "injected")]),
    ]


def test_days_collapses_identical_injections_into_a_count():
    # Two different torrents injected on the same tracker in the same minute
    # (seen in real logs): shown once, with a count.
    events = [
        _event("2026-09-18 18:46:37.386", "TrackerD", "aaaaaaaa", "11111111", source_name="RD"),
        _event("2026-09-18 18:46:30.492", "TrackerD", "bbbbbbbb", "11111111", source_name="RD"),
    ]

    entries = group_events(events)[0].days[0].entries

    assert entries == [DayEntry("TrackerD", "18:46", "injected", count=2)]


def test_days_keeps_same_tracker_apart_when_minutes_differ():
    events = [
        _event("2026-09-18 18:47:00.000", "TrackerD", "aaaaaaaa", "11111111", source_name="RD"),
        _event("2026-09-18 18:46:00.000", "TrackerD", "bbbbbbbb", "11111111", source_name="RD"),
    ]

    entries = group_events(events)[0].days[0].entries

    assert [(e.time, e.count) for e in entries] == [("18:47", 1), ("18:46", 1)]


def test_summarize_counts_cross_seeds_by_period():
    events = [
        _event("2026-09-24 09:00:00.000", "TrackerA", "aaaaaaaa", "11111111"),
        _event("2026-09-18 10:00:00.000", "TrackerB", "bbbbbbbb", "11111111"),  # 7th day back
        _event("2026-09-17 10:00:00.000", "TrackerA", "cccccccc", "22222222"),
        _event("2026-08-31 10:00:00.000", "TrackerA", "dddddddd", "33333333"),
    ]

    stats = summarize(group_events(events), date(2026, 9, 24))

    assert stats == AddedStats(
        cross_seeds=4,
        today=1,
        last_7_days=2,
        this_month=3,
        top_trackers=[("TrackerA", 3), ("TrackerB", 1)],
    )
