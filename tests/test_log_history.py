from pathlib import Path

from app.log_history import (
    day_label,
    list_available_days,
    list_rotated_log_files,
    read_all_events,
    read_day_entries,
    read_log_file,
)


def _write_match_line(path, timestamp: str, name: str, tracker: str, outcome: str = "injected") -> None:
    with path.open("a") as f:
        f.write(
            f"{timestamp} info: [rss] Found {name} [aaaaaaaa...] on {tracker} "
            f"by MATCH from torrentClient ({name} [bbbbbbbb...@client]) - {outcome}\n"
        )


def test_list_rotated_log_files_excludes_current_symlink_and_sorts_chronologically(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    day1 = logs_dir / "verbose.2026-09-14.log"
    day2 = logs_dir / "verbose.2026-09-15.log"
    day1.write_text("")
    day2.write_text("")
    (logs_dir / "verbose.current.log").symlink_to(day2)

    files = list_rotated_log_files(logs_dir)

    assert files == [day1, day2]


def test_list_rotated_log_files_returns_empty_list_when_dir_missing(tmp_path):
    assert list_rotated_log_files(tmp_path / "missing") == []


def test_read_all_events_aggregates_across_files_newest_first(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    day1 = logs_dir / "verbose.2026-09-14.log"
    _write_match_line(day1, "2026-09-14 10:00:00.000", "Movie.One", "TrackerA")
    day2 = logs_dir / "verbose.2026-09-15.log"
    _write_match_line(day2, "2026-09-15 09:00:00.000", "Movie.Two", "TrackerB")
    (logs_dir / "verbose.current.log").symlink_to(day2)

    events = read_all_events(logs_dir)

    assert [event.name for event in events] == ["Movie.Two", "Movie.One"]


def test_read_all_events_excludes_non_successful_outcomes(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    day1 = logs_dir / "verbose.2026-09-14.log"
    _write_match_line(day1, "2026-09-14 10:00:00.000", "Movie.One", "TrackerA", outcome="injected")
    _write_match_line(day1, "2026-09-14 11:00:00.000", "Movie.Failed", "TrackerA", outcome="failed to inject, saving...")

    events = read_all_events(logs_dir)

    assert [event.name for event in events] == ["Movie.One"]


def test_read_all_events_respects_max_events_cap(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    day1 = logs_dir / "verbose.2026-09-14.log"
    _write_match_line(day1, "2026-09-14 10:00:00.000", "Movie.One", "TrackerA")
    _write_match_line(day1, "2026-09-14 11:00:00.000", "Movie.Two", "TrackerA")

    events = read_all_events(logs_dir, max_events=1)

    assert [event.name for event in events] == ["Movie.Two"]


def test_read_all_events_returns_empty_list_when_dir_missing(tmp_path):
    assert read_all_events(tmp_path / "missing") == []


def test_read_all_events_ignores_surrounding_noise_lines(tmp_path):
    """Guards the line pre-filter added for performance: unrelated log lines
    (including ones that don't start with a timestamp) around a real MATCH
    line must not suppress or corrupt it."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    day1 = logs_dir / "verbose.2026-09-14.log"
    day1.write_text(
        "2026-09-14 09:00:00.000 verbose: [rss] polling indexer feed\n"
        "  continuation line with no timestamp\n"
        "2026-09-14 09:05:00.000 error: [rss] some unrelated error\n"
    )
    _write_match_line(day1, "2026-09-14 10:00:00.000", "Movie.One", "TrackerA")
    with day1.open("a") as f:
        f.write("2026-09-14 10:05:00.000 verbose: [http] more unrelated noise\n")

    events = read_all_events(logs_dir)

    assert [event.name for event in events] == ["Movie.One"]


def test_read_all_events_tolerates_invalid_utf8_in_one_file(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    good = logs_dir / "verbose.2026-09-14.log"
    _write_match_line(good, "2026-09-14 10:00:00.000", "Movie.One", "TrackerA")
    bad = logs_dir / "verbose.2026-09-15.log"
    bad.write_bytes(b"\xff\xfe not valid utf-8")

    events = read_all_events(logs_dir)

    assert [event.name for event in events] == ["Movie.One"]


def test_day_label_strips_prefix_and_suffix():
    assert day_label(Path("verbose.2026-09-15.log")) == "2026-09-15"


def test_list_available_days_excludes_current_and_sorts_newest_first(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    day1 = logs_dir / "verbose.2026-09-14.log"
    day2 = logs_dir / "verbose.2026-09-15.log"
    day3 = logs_dir / "verbose.2026-09-13.log"
    day1.write_text("")
    day2.write_text("")
    day3.write_text("")
    (logs_dir / "verbose.current.log").symlink_to(day2)

    # day2 is today (the symlink target) and must not appear twice: it's
    # already offered as "Today" in the UI.
    assert list_available_days(logs_dir) == ["2026-09-14", "2026-09-13"]


def test_read_day_entries_parses_the_matching_rotated_file(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    day1 = logs_dir / "verbose.2026-09-14.log"
    day1.write_text("2026-09-14 10:00:00.000 info: [x] entry from day1\n")
    day2 = logs_dir / "verbose.2026-09-15.log"
    day2.write_text("2026-09-15 10:00:00.000 info: [x] entry from day2\n")

    entries = read_day_entries(logs_dir, "2026-09-14")

    assert [e.message for e in entries] == ["entry from day1"]


def test_read_day_entries_returns_empty_list_for_unknown_day(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    assert read_day_entries(logs_dir, "2026-01-01") == []


def test_read_day_entries_tolerates_invalid_utf8(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    day1 = logs_dir / "verbose.2026-09-14.log"
    day1.write_bytes(
        "2026-09-14 10:00:00.000 info: [x] entry with \xe9 accent\n".encode("latin-1")
    )

    entries = read_day_entries(logs_dir, "2026-09-14")

    assert len(entries) == 1


def test_read_log_file_returns_empty_list_when_file_missing(tmp_path):
    assert read_log_file(tmp_path / "verbose.current.log") == []


def test_read_all_events_picks_up_lines_appended_to_a_cached_file(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    day1 = logs_dir / "verbose.2026-09-14.log"
    _write_match_line(day1, "2026-09-14 10:00:00.000", "Movie.One", "TrackerA")
    assert [e.name for e in read_all_events(logs_dir)] == ["Movie.One"]

    _write_match_line(day1, "2026-09-14 11:00:00.000", "Movie.Two", "TrackerA")

    assert [e.name for e in read_all_events(logs_dir)] == ["Movie.Two", "Movie.One"]
