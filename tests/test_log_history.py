from app.log_history import list_rotated_log_files, read_all_events


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
