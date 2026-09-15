import pytest

from app.crossseed_config import (
    TorznabBlockError,
    backup_config,
    extract_current_urls,
    find_torznab_block,
    read_config,
    replace_torznab_block,
    write_config,
)


FLAT_ARRAY_CONFIG = """module.exports = {
  torznab: [
    "http://prowlarr:9696/1/api?apikey=old",
    "http://prowlarr:9696/2/api?apikey=old"
  ],
  delay: 30,
};
"""

MAP_STYLE_CONFIG = """module.exports = {
  torznab: [1, 2, 6].map(
    (id) => `http://prowlarr:9696/${id}/api?apikey=old`
  ),
  delay: 30,
};
"""

FLAT_ARRAY_WITH_COMMENT = """module.exports = {
  torznab: [
    "http://prowlarr:9696/1/api?apikey=old", // see docs ] for format
    "http://prowlarr:9696/2/api?apikey=old"
  ],
  delay: 30,
};
"""

FLAT_ARRAY_WITH_BLOCK_COMMENT = """module.exports = {
  torznab: [
    "http://prowlarr:9696/1/api?apikey=old", /* see docs ] and ) for format */
    "http://prowlarr:9696/2/api?apikey=old"
  ],
  delay: 30,
};
"""

FLAT_ARRAY_WITH_UNTERMINATED_BLOCK_COMMENT = """module.exports = {
  torznab: [
    "http://prowlarr:9696/1/api?apikey=old", /* unterminated
    "http://prowlarr:9696/2/api?apikey=old"
  ],
  delay: 30,
};
"""


def test_find_torznab_block_locates_flat_array():
    start, end = find_torznab_block(FLAT_ARRAY_CONFIG)
    assert FLAT_ARRAY_CONFIG[start:end].strip().startswith("[")
    assert FLAT_ARRAY_CONFIG[start:end].strip().endswith("]")


def test_find_torznab_block_locates_map_style_including_call():
    start, end = find_torznab_block(MAP_STYLE_CONFIG)
    snippet = MAP_STYLE_CONFIG[start:end]
    assert snippet.strip().startswith("[1, 2, 6]")
    assert snippet.rstrip().endswith(")")


def test_find_torznab_block_raises_when_key_missing():
    with pytest.raises(TorznabBlockError):
        find_torznab_block("module.exports = { delay: 30 };")


def test_find_torznab_block_raises_when_key_appears_twice():
    text = "torznab: [],\ntorznab: []"
    with pytest.raises(TorznabBlockError):
        find_torznab_block(text)


def test_extract_current_urls_reads_flat_array():
    urls = extract_current_urls(FLAT_ARRAY_CONFIG)
    assert urls == [
        "http://prowlarr:9696/1/api?apikey=old",
        "http://prowlarr:9696/2/api?apikey=old",
    ]


def test_replace_torznab_block_normalizes_flat_array():
    result = replace_torznab_block(
        FLAT_ARRAY_CONFIG,
        ["http://prowlarr:9696/1/api?apikey=new"],
    )

    assert '"http://prowlarr:9696/1/api?apikey=new"' in result
    assert "old" not in result
    assert "delay: 30" in result  # le reste du fichier est préservé


def test_replace_torznab_block_normalizes_map_style():
    result = replace_torznab_block(
        MAP_STYLE_CONFIG,
        ["http://prowlarr:9696/1/api?apikey=new"],
    )

    assert '"http://prowlarr:9696/1/api?apikey=new"' in result
    assert ".map(" not in result
    assert "delay: 30" in result


def test_backup_config_creates_timestamped_copy(tmp_path):
    config_path = tmp_path / "config.js"
    config_path.write_text(FLAT_ARRAY_CONFIG)

    backup_path = backup_config(config_path)

    assert backup_path.exists()
    assert backup_path.name.startswith("config.js.bak.")
    assert backup_path.read_text() == FLAT_ARRAY_CONFIG


def test_read_and_write_config_roundtrip(tmp_path):
    config_path = tmp_path / "config.js"
    config_path.write_text(FLAT_ARRAY_CONFIG)

    text = read_config(config_path)
    write_config(config_path, text.replace("old", "new"))

    assert "new" in config_path.read_text()


def test_replace_torznab_block_handles_inline_comments():
    """Test that inline // comments inside torznab array are correctly skipped."""
    result = replace_torznab_block(
        FLAT_ARRAY_WITH_COMMENT,
        ["http://prowlarr:9696/1/api?apikey=new"],
    )

    assert '"http://prowlarr:9696/1/api?apikey=new"' in result
    assert "old" not in result
    assert "delay: 30" in result  # rest of file preserved
    # Ensure the comment didn't corrupt parsing
    assert result.count("[") == result.count("]")


def test_backup_config_preserves_line_endings(tmp_path):
    """Test that backup preserves exact byte content, including \\r\\n line endings."""
    config_path = tmp_path / "config.js"
    original_bytes = FLAT_ARRAY_CONFIG.replace("\n", "\r\n").encode("utf-8")
    config_path.write_bytes(original_bytes)

    backup_path = backup_config(config_path)

    assert backup_path.exists()
    assert backup_path.read_bytes() == original_bytes


def test_read_and_write_config_preserve_crlf_line_endings(tmp_path):
    """read_config/write_config must not silently normalize CRLF to LF."""
    config_path = tmp_path / "config.js"
    original_bytes = FLAT_ARRAY_CONFIG.replace("\n", "\r\n").encode("utf-8")
    config_path.write_bytes(original_bytes)

    text = read_config(config_path)
    write_config(config_path, text)

    assert config_path.read_bytes() == original_bytes


def test_replace_torznab_block_handles_inline_block_comments():
    """Test that inline /* ... */ comments inside torznab array are correctly
    skipped, even when they contain ] or ) that could confuse naive parsing."""
    result = replace_torznab_block(
        FLAT_ARRAY_WITH_BLOCK_COMMENT,
        ["http://prowlarr:9696/1/api?apikey=new"],
    )

    assert '"http://prowlarr:9696/1/api?apikey=new"' in result
    assert "old" not in result
    assert "delay: 30" in result
    assert result.count("[") == result.count("]")


def test_replace_torznab_block_raises_on_unterminated_block_comment():
    """An unterminated /* must raise rather than silently mis-parsing the
    rest of the file."""
    with pytest.raises(TorznabBlockError):
        replace_torznab_block(
            FLAT_ARRAY_WITH_UNTERMINATED_BLOCK_COMMENT,
            ["http://prowlarr:9696/1/api?apikey=new"],
        )
