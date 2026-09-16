import time

from app.crossseed_events import CrossSeedEvent, extract_events
from app.log_parser import LogEntry


def test_extract_events_matches_successful_injected_line():
    entry = LogEntry(
        timestamp="2026-09-11 11:26:46.414",
        level="info",
        component="rss",
        message=(
            "Found Zootopia.2.2025.2160p.DV.HDR.WEBRip.x265-ESPER.mkv [621d83e9...] on V3X "
            "by MATCH from torrentClient (Zootopia.2.2025.2160p.DV.HDR.WEBRip.x265-ESPER.mkv "
            "[7cf6d506...@192.168.134.10:8090]) - injected"
        ),
    )

    events = extract_events([entry])

    assert events == [
        CrossSeedEvent(
            timestamp="2026-09-11 11:26:46.414",
            name="Zootopia.2.2025.2160p.DV.HDR.WEBRip.x265-ESPER.mkv",
            tracker="V3X",
            outcome="injected",
            component="rss",
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
            "Found Chappie (2015) MULTi VFF 2160p BluRay x265 TrueHD Atmos-XANDER.mkv "
            "[a459eb1b...] on The Old School (API) by MATCH from torrentClient "
            "(Chappie (2015) MULTi VFF 2160p BluRay x265 TrueHD Atmos-XANDER.mkv "
            "[eaebde2a...@192.168.134.10:8090]) - injected"
        ),
    )

    events = extract_events([entry])

    assert events[0].name == "Chappie (2015) MULTi VFF 2160p BluRay x265 TrueHD Atmos-XANDER.mkv"
    assert events[0].tracker == "The Old School (API)"


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
            "Found Fight.Club.1999.1080p.BLURAY.x264-FoX.mkv [3b677ec9...] on TR4KER "
            "by MATCH from torrentClient (Fight.Club.1999.1080p.BLURAY.x264-FoX.mkv "
            "[5d598488...@192.168.134.10:8090]) - failed to inject, saving..."
        ),
    )

    assert extract_events([entry]) == []


def test_extract_events_excludes_already_exists_outcome():
    entry = LogEntry(
        timestamp="2026-09-13 08:08:08.939",
        level="verbose",
        component="inject",
        message=(
            "Found Some.Show.S12E04.1080p.mkv [01e6dd4c...] on TR4KER "
            "by MATCH from torrentClient (Some.Show.S12E04.1080p.mkv "
            "[4d3a6e84...@192.168.134.10:8090]) - exists"
        ),
    )

    assert extract_events([entry]) == []


def test_extract_events_ignores_inject_linking_lines():
    entry = LogEntry(
        timestamp="2026-09-02 00:15:28.689",
        level="verbose",
        component="inject",
        message="Linking Some.Movie.2024.1080p.mkv [79cb2e52...] from Some.Movie.2024.1080p.mkv [1348f034...@client] to /downloads/complete",
    )

    assert extract_events([entry]) == []


def test_extract_events_ignores_injection_failed_error_lines():
    entry = LogEntry(
        timestamp="2026-09-02 00:15:54.924",
        level="error",
        component="qbittorrent@192.168.134.10:8090",
        message="Injection failed for Some.Movie.2024.1080p.mkv [79cb2e52...]: Failed to retrieve torrent after adding",
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
            "Found Zootopia.2.2025.2160p.DV.HDR.WEBRip.x265-ESPER.mkv [621d83e9...] on V3X "
            "by MATCH from torrentClient (Zootopia.2.2025.2160p.DV.HDR.WEBRip.x265-ESPER.mkv "
            "[7cf6d506...@192.168.134.10:8090]) - injected"
            "\n    at Object.<anonymous> (/app/x.js:1:1)"
        ),
    )

    events = extract_events([entry])

    assert events == [
        CrossSeedEvent(
            timestamp="2026-09-11 11:26:46.414",
            name="Zootopia.2.2025.2160p.DV.HDR.WEBRip.x265-ESPER.mkv",
            tracker="V3X",
            outcome="injected",
            component="rss",
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
