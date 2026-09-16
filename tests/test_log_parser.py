from app.log_parser import LogEntry, parse_log_lines


def test_parse_log_lines_parses_standard_entry():
    lines = ["2026-09-15 00:19:28.390 info: [scheduler] starting job: inject"]

    entries = parse_log_lines(lines)

    assert entries == [
        LogEntry(
            timestamp="2026-09-15 00:19:28.390",
            level="info",
            component="scheduler",
            message="starting job: inject",
        )
    ]


def test_parse_log_lines_parses_multiple_entries():
    lines = [
        "2026-09-15 00:19:28.390 info: [scheduler] starting job: inject",
        "2026-09-15 00:19:29.100 verbose: [rss] checking feed",
    ]

    entries = parse_log_lines(lines)

    assert [e.component for e in entries] == ["scheduler", "rss"]


def test_parse_log_lines_attaches_continuation_lines_without_timestamp():
    lines = [
        "2026-09-15 00:19:30.000 error: [qbittorrent] injection failed",
        "    at Object.inject (/app/dist/index.js:123:45)",
        "    at processTicksAndRejections (node:internal/process/task_queues:95:5)",
    ]

    entries = parse_log_lines(lines)

    assert len(entries) == 1
    assert entries[0].message == (
        "injection failed\n"
        "    at Object.inject (/app/dist/index.js:123:45)\n"
        "    at processTicksAndRejections (node:internal/process/task_queues:95:5)"
    )


def test_parse_log_lines_drops_leading_lines_before_any_timestamped_entry():
    lines = ["some stray line with no entry to attach to", "2026-09-15 00:00:00.000 info: [x] real entry"]

    entries = parse_log_lines(lines)

    assert len(entries) == 1
    assert entries[0].message == "real entry"


def test_parse_log_lines_returns_empty_list_for_no_lines():
    assert parse_log_lines([]) == []


def test_parse_log_lines_treats_bracket_less_lines_as_their_own_entry():
    # Real cross-seed logs emit some lines with no [component] at all
    # (e.g. "verbose: Unlinking ...", "debug: request failed ..."). These
    # must become their own entry, not get glued onto the previous one.
    lines = [
        "2026-09-02 00:15:54.926 error: [inject] Found Movie.mkv [aaaaaaaa...] on TrackerX "
        "by MATCH from torrentClient (Movie.mkv [bbbbbbbb...@client]) - failed to inject, saving...",
        "2026-09-02 00:15:54.930 verbose: Unlinking /data/torrents/completed/Movie.mkv",
    ]

    entries = parse_log_lines(lines)

    assert len(entries) == 2
    assert entries[0].message.endswith("- failed to inject, saving...")
    assert entries[1] == LogEntry(
        timestamp="2026-09-02 00:15:54.930",
        level="verbose",
        component="",
        message="Unlinking /data/torrents/completed/Movie.mkv",
    )
