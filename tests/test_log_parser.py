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
