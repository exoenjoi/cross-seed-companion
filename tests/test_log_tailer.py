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


def test_read_recent_entries_returns_empty_list_when_file_missing(tmp_path):
    missing = tmp_path / "verbose.current.log"

    assert read_recent_entries(missing) == []


def test_log_tailer_only_returns_lines_appended_after_first_open(tmp_path):
    current, target = _make_current_log(
        tmp_path, "verbose.2026-09-15.log", "2026-09-15 00:00:00.000 info: [x] old entry\n"
    )
    tailer = LogTailer(current)

    assert tailer.read_new_entries() == []  # rien de nouveau, l'ancien contenu n'est pas rejoué

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
    tailer.read_new_entries()  # premier open : pas de contenu ancien rejoué

    with day1.open("a") as f:
        f.write("2026-09-14 23:59:30.000 info: [x] last entry of day1\n")
    assert tailer.read_new_entries() == []  # "last entry of day1" est en attente (pas encore refermée)

    day2 = tmp_path / "verbose.2026-09-15.log"
    day2.write_text("2026-09-15 00:00:00.000 info: [x] first entry of day2\n")
    current.unlink()
    current.symlink_to(day2)

    entries = tailer.read_new_entries()

    # la rotation doit "libérer" l'entrée en attente de day1, même si day2 a déjà
    # sa propre entrée qui reste elle-même en attente (pas encore refermée)
    assert [e.message for e in entries] == ["last entry of day1"]
