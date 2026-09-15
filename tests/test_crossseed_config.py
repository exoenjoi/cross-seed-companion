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
