import re
from datetime import datetime
from pathlib import Path

_QUOTE_CHARS = "\"'`"
_TORZNAB_KEY_RE = re.compile(r"\btorznab\s*:\s*")
_MAP_CALL_RE = re.compile(r"\s*\.map\s*\(")


class TorznabBlockError(Exception):
    """Levée quand le bloc 'torznab:' de config.js ne peut pas être repéré sans ambiguïté."""


def _skip_string(text: str, pos: int) -> int:
    quote = text[pos]
    i = pos + 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == quote:
            return i + 1
        i += 1
    raise TorznabBlockError("Chaîne de caractères non terminée dans config.js.")


def _skip_line_comment(text: str, pos: int) -> int:
    """Skip from // to end of line."""
    i = pos + 2  # Skip the //
    while i < len(text) and text[i] not in "\n\r":
        i += 1
    return i


def _skip_block_comment(text: str, pos: int) -> int:
    """Skip from /* to matching */."""
    i = pos + 2  # Skip the /*
    while i < len(text) - 1:
        if text[i:i+2] == "*/":
            return i + 2
        i += 1
    raise TorznabBlockError("Commentaire non terminé (/* sans */) dans config.js.")


def _find_matching(text: str, open_pos: int, open_ch: str, close_ch: str) -> int:
    depth = 0
    i = open_pos
    while i < len(text):
        ch = text[i]
        # Check for comments first
        if i < len(text) - 1 and text[i:i+2] == "//":
            i = _skip_line_comment(text, i)
            continue
        if i < len(text) - 1 and text[i:i+2] == "/*":
            i = _skip_block_comment(text, i)
            continue
        # Check for strings
        if ch in _QUOTE_CHARS:
            i = _skip_string(text, i)
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise TorznabBlockError(f"'{open_ch}' non refermé dans config.js.")


def _mask_comments_and_strings(text: str) -> str:
    """Return `text` with comment/string contents blanked out (same length),
    so keyword matching can ignore anything inside a // , /* */ or quote."""
    masked = list(text)
    i = 0
    n = len(text)
    while i < n:
        if text[i:i + 2] == "//":
            end = _skip_line_comment(text, i)
        elif text[i:i + 2] == "/*":
            end = _skip_block_comment(text, i)
        elif text[i] in _QUOTE_CHARS:
            end = _skip_string(text, i)
        else:
            i += 1
            continue
        for j in range(i, end):
            masked[j] = " "
        i = end
    return "".join(masked)


def find_torznab_block(config_text: str) -> tuple[int, int]:
    masked_text = _mask_comments_and_strings(config_text)
    matches = list(_TORZNAB_KEY_RE.finditer(masked_text))
    if len(matches) != 1:
        raise TorznabBlockError(
            f"'torznab:' doit apparaître exactement une fois dans config.js "
            f"(trouvé {len(matches)} fois). Abandon sans rien écrire."
        )
    array_start = matches[0].end()
    if array_start >= len(config_text) or config_text[array_start] != "[":
        raise TorznabBlockError("'torznab:' doit être suivi d'un tableau '['.")

    array_end = _find_matching(config_text, array_start, "[", "]")
    end = array_end

    map_match = _MAP_CALL_RE.match(config_text, array_end)
    if map_match:
        call_open = map_match.end() - 1  # index du '(' d'ouverture
        end = _find_matching(config_text, call_open, "(", ")")

    return array_start, end


def extract_current_urls(config_text: str) -> list[str]:
    start, end = find_torznab_block(config_text)
    block = config_text[start:end]
    return re.findall(r'"([^"]*)"', block)


def replace_torznab_block(config_text: str, urls: list[str]) -> str:
    start, end = find_torznab_block(config_text)
    lines = "".join(f'    "{url}",\n' for url in urls)
    array_literal = f"[\n{lines}  ]"
    return config_text[:start] + array_literal + config_text[end:]


def read_config(path: Path) -> str:
    # newline="" disables universal-newline translation so CRLF/CR content
    # round-trips through read_config/write_config unchanged.
    with path.open("r", newline="") as f:
        return f.read()


def backup_config(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_path = path.with_name(f"{path.name}.bak.{timestamp}")
    backup_path.write_bytes(path.read_bytes())
    return backup_path


def write_config(path: Path, new_text: str) -> None:
    with path.open("w", newline="") as f:
        f.write(new_text)
