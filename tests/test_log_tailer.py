from app.log_tailer import LogTailer, read_recent_entries


def _make_current_log(tmp_path, target_name: str, content: str):
    target = tmp_path / target_name
    target.write_text(content)
    current = tmp_path / "verbose.current.log"
    if current.exists() or current.is_symlink():
        current.unlink()
    current.symlink_to(target)
    return current, target


def test_read_recent_entries_returns_last_n_entries(tmp_path):
    lines = "\n".join(
        f"2026-09-15 00:00:{i:02d}.000 info: [x] entry {i}" for i in range(5)
    )
    current, _ = _make_current_log(tmp_path, "verbose.2026-09-15.log", lines + "\n")

    entries = read_recent_entries(current, max_entries=2)

    assert [e.message for e in entries] == ["entry 3", "entry 4"]


def test_read_recent_entries_tolerates_invalid_utf8(tmp_path):
    # Same encoding issue as app/log_history.py's Finding 3 fix: a bad byte
    # must not crash the whole backfill, just get replaced.
    current, target = _make_current_log(tmp_path, "verbose.2026-09-15.log", "")
    target.write_bytes(
        "2026-09-15 00:00:00.000 info: [x] entry with \xe9 accent\n".encode("latin-1")
        + b"2026-09-15 00:00:01.000 info: [x] clean entry\n"
    )

    entries = read_recent_entries(current)

    assert entries[-1].message == "clean entry"


def test_log_tailer_tolerates_invalid_utf8_while_polling(tmp_path):
    current, target = _make_current_log(
        tmp_path, "verbose.2026-09-15.log", "2026-09-15 00:00:00.000 info: [x] old entry\n"
    )
    tailer = LogTailer(current)
    tailer.read_new_entries()  # seeks to EOF on first open

    with target.open("ab") as f:
        f.write("2026-09-15 00:00:01.000 info: [x] entry with \xe9 accent\n".encode("latin-1"))
        f.write(b"2026-09-15 00:00:02.000 info: [x] clean entry\n")
        f.write(b"2026-09-15 00:00:03.000 info: [x] third entry\n")

    entries = tailer.read_new_entries()

    assert entries[-1].message == "clean entry"


def test_read_recent_entries_returns_empty_list_when_file_missing(tmp_path):
    missing = tmp_path / "verbose.current.log"

    assert read_recent_entries(missing) == []


def test_log_tailer_only_returns_lines_appended_after_first_open(tmp_path):
    current, target = _make_current_log(
        tmp_path, "verbose.2026-09-15.log", "2026-09-15 00:00:00.000 info: [x] old entry\n"
    )
    tailer = LogTailer(current)

    assert tailer.read_new_entries() == []  # nothing new, old content is not replayed

    with target.open("a") as f:
        f.write("2026-09-15 00:00:01.000 info: [x] new entry\n")
        f.write("2026-09-15 00:00:02.000 info: [x] entry after, closes the previous one\n")

    entries = tailer.read_new_entries()

    assert [e.message for e in entries] == ["new entry"]


def test_log_tailer_detects_symlink_rotation_and_flushes_pending_entry(tmp_path):
    current, day1 = _make_current_log(
        tmp_path, "verbose.2026-09-14.log", "2026-09-14 23:59:00.000 info: [x] day1 entry\n"
    )
    tailer = LogTailer(current)
    tailer.read_new_entries()  # first open: old content is not replayed

    with day1.open("a") as f:
        f.write("2026-09-14 23:59:30.000 info: [x] last entry of day1\n")
    assert tailer.read_new_entries() == []  # "last entry of day1" is pending (not yet closed)

    day2 = tmp_path / "verbose.2026-09-15.log"
    day2.write_text("2026-09-15 00:00:00.000 info: [x] first entry of day2\n")
    current.unlink()
    current.symlink_to(day2)

    entries = tailer.read_new_entries()

    # rotation must "release" the pending entry of day1, even if day2 already
    # has its own entry that is itself still pending (not yet closed)
    assert [e.message for e in entries] == ["last entry of day1"]


def test_log_tailer_flushes_unread_lines_from_outgoing_day_on_rotation(tmp_path):
    """Regression test: lines appended to today's file in the same poll
    window as the day's rotation must not be dropped."""
    current, day1 = _make_current_log(
        tmp_path, "verbose.2026-09-14.log", "2026-09-14 23:58:00.000 info: [x] backfill entry\n"
    )
    tailer = LogTailer(current)
    tailer.read_new_entries()  # first open: old content is not replayed

    # These two lines were never read by an intermediate poll.
    with day1.open("a") as f:
        f.write("2026-09-14 23:59:00.000 info: [x] last entry before rotation\n")
        f.write("2026-09-14 23:59:30.000 info: [x] closes the previous one\n")

    day2 = tmp_path / "verbose.2026-09-15.log"
    day2.write_text("2026-09-15 00:00:00.000 info: [x] first entry of day2\n")
    current.unlink()
    current.symlink_to(day2)

    entries = tailer.read_new_entries()

    assert [e.message for e in entries] == [
        "last entry before rotation",
        "closes the previous one",
    ]


def test_log_tailer_handles_rotation_race_when_new_file_not_yet_created(tmp_path):
    """Test that tailer doesn't get permanently stuck if symlink target doesn't exist yet.

    Scenario: cross-seed rotates the symlink before finishing the new file.
    Tailer should retry on next call, not cache a "seen" state for a missing file.
    """
    current, day1 = _make_current_log(
        tmp_path, "verbose.2026-09-14.log", "2026-09-14 23:59:00.000 info: [x] day1 entry\n"
    )
    tailer = LogTailer(current)
    tailer.read_new_entries()

    # Append pending entry on day1
    with day1.open("a") as f:
        f.write("2026-09-14 23:59:30.000 info: [x] pending entry\n")
    assert tailer.read_new_entries() == []

    # Rotate symlink to day2, but day2 doesn't exist yet (race condition)
    day2_path = tmp_path / "verbose.2026-09-15.log"
    current.unlink()
    current.symlink_to(day2_path)

    # First call with missing target: should flush pending from day1 but can't read new file
    entries = tailer.read_new_entries()
    assert [e.message for e in entries] == ["pending entry"]

    # Now day2 file appears
    day2_path.write_text("2026-09-15 00:00:00.000 info: [x] first entry of day2\n")

    # Next call should successfully read from day2 (not be permanently stuck)
    entries = tailer.read_new_entries()
    assert [e.message for e in entries] == []  # day2's first entry is pending, not closed


def test_log_tailer_handles_missing_symlink_at_startup(tmp_path):
    """Test that symlink missing at startup doesn't consume first-open EOF-seek.

    Scenario: app starts before cross-seed creates today's file.
    When file appears, tailer should seek to EOF (backfill separate), not read from byte 0.
    """
    current = tmp_path / "verbose.current.log"

    # LogTailer created with non-existent symlink
    tailer = LogTailer(current)

    # First call with missing symlink: should return []
    assert tailer.read_new_entries() == []

    # Now create the file with existing content (simulating backfill already shown to user)
    day1 = tmp_path / "verbose.2026-09-15.log"
    day1.write_text("2026-09-15 00:00:00.000 info: [x] old entry already shown by backfill\n")
    current.symlink_to(day1)

    # Next call should seek to EOF (not re-show old content)
    entries = tailer.read_new_entries()
    assert entries == []  # EOF seek means no content returned

    # Append new content
    with day1.open("a") as f:
        f.write("2026-09-15 00:00:01.000 info: [x] new entry\n")
        f.write("2026-09-15 00:00:02.000 info: [x] closes previous\n")

    # Now should get just the new entry
    entries = tailer.read_new_entries()
    assert [e.message for e in entries] == ["new entry"]


def test_log_tailer_close_releases_file_handle(tmp_path):
    """Test that close() releases the underlying file handle."""
    current, target = _make_current_log(
        tmp_path, "verbose.2026-09-15.log", "2026-09-15 00:00:00.000 info: [x] entry\n"
    )
    tailer = LogTailer(current)
    tailer.read_new_entries()  # Opens the file

    # File should be open before close
    assert tailer._file is not None

    # Close should release the file handle
    tailer.close()

    # File should be None after close
    assert tailer._file is None

    # Closing again should not raise an error
    tailer.close()
    assert tailer._file is None


def test_log_tailer_treats_bracket_less_line_as_its_own_entry(tmp_path):
    # Same real-log edge case as log_parser: some lines have no [component]
    # at all (e.g. "verbose: Unlinking ..."). The tailer has its own inline
    # copy of the match/continuation logic and must not glue these onto the
    # previous pending entry either.
    current, target = _make_current_log(
        tmp_path, "verbose.2026-09-15.log", "2026-09-15 00:00:00.000 info: [x] old entry\n"
    )
    tailer = LogTailer(current)
    tailer.read_new_entries()  # seeks to EOF on first open; "old entry" is backfill, never read here

    with target.open("a") as f:
        f.write("2026-09-15 00:00:01.000 error: [inject] first entry\n")
        f.write("2026-09-15 00:00:02.000 verbose: Unlinking /data/torrents/Movie.mkv\n")
        f.write("2026-09-15 00:00:03.000 info: [x] third entry\n")

    entries = tailer.read_new_entries()

    assert [e.message for e in entries] == [
        "first entry",
        "Unlinking /data/torrents/Movie.mkv",
    ]
    bracket_less = entries[-1]
    assert bracket_less.component == ""
    assert bracket_less.level == "verbose"
