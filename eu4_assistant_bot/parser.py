from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Legacy PoC regex (used by _LegacyClausewitzParser / EU4RulesLoader) ──────
_PAIR = re.compile(r'(?P<key>[A-Za-z0-9_.\\-]+)\s*=\s*(?P<value>.+)')

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# ClausewitzTextParser  — full recursive parser (M3)
# ─────────────────────────────────────────────────────────────────────────────

_DATE_RE = re.compile(r'^\d{1,4}\.\d{1,2}\.\d{1,2}$')
_INT_RE  = re.compile(r'^-?\d+$')
_FLOAT_RE = re.compile(r'^-?\d+\.\d+$')


def _coerce(token: str) -> Any:
    """Convert a raw Clausewitz scalar token to a Python type."""
    if token == "yes":
        return True
    if token == "no":
        return False
    if _DATE_RE.match(token):
        return token  # keep dates as-is
    if _INT_RE.match(token):
        return int(token)
    if _FLOAT_RE.match(token):
        return float(token)
    return token


def _set_key(d: dict[str, Any], key: str, value: Any) -> None:
    """Insert value into dict; repeated keys become a list."""
    if key in d:
        existing = d[key]
        if isinstance(existing, list):
            existing.append(value)
        else:
            d[key] = [existing, value]
    else:
        d[key] = value


def _tokenize(text: str) -> list[str]:
    """
    Split Clausewitz text into a flat token stream.
    Strips full-line and inline comments. Preserves quoted strings as one token.
    """
    tokens: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        # skip whitespace
        if c in ' \t\r\n':
            i += 1
            continue
        # full-line or inline comment — skip to end of line
        if c == '#':
            while i < n and text[i] != '\n':
                i += 1
            continue
        # structural chars
        if c in '{}=':
            tokens.append(c)
            i += 1
            continue
        # quoted string
        if c == '"':
            i += 1
            start = i
            while i < n and text[i] != '"':
                i += 1
            tokens.append(text[start:i])
            i += 1  # closing quote
            continue
        # bare token (key, value, or scalar list element)
        start = i
        while i < n and text[i] not in ' \t\r\n#{}="':
            i += 1
        tokens.append(text[start:i])
    return tokens


def _parse_block(tokens: list[str], pos: int) -> tuple[dict[str, Any], int]:
    """
    Parse a block starting at pos (after the opening '{').
    Returns (dict, new_pos) where new_pos points past the closing '}'.
    """
    result: dict[str, Any] = {}
    n = len(tokens)

    while pos < n:
        tok = tokens[pos]

        if tok == '}':
            return result, pos + 1

        # key = value / key = { ... }
        if pos + 1 < n and tokens[pos + 1] == '=':
            key = tok
            pos += 2  # skip key and '='
            if pos >= n:
                break

            if tokens[pos] == '{':
                pos += 1  # skip '{'
                # anonymous block list: { { ... } { ... } }
                if pos < n and tokens[pos] == '{':
                    block_list: list[dict[str, Any]] = []
                    while pos < n and tokens[pos] != '}':
                        if tokens[pos] == '{':
                            pos += 1  # skip inner '{'
                            child, pos = _parse_block(tokens, pos)
                            block_list.append(child)
                        else:
                            pos += 1  # skip unexpected tokens
                    pos += 1  # skip outer '}'
                    _set_key(result, key, block_list)
                else:
                    # peek: is this a scalar list or a block?
                    # scalar list: no '=' inside before first '}'
                    peek = pos
                    is_scalar_list = True
                    while peek < n and tokens[peek] != '}':
                        if tokens[peek] == '=':
                            is_scalar_list = False
                            break
                        peek += 1

                    if is_scalar_list:
                        # collect scalars until '}'
                        items: list[Any] = []
                        while pos < n and tokens[pos] != '}':
                            items.append(_coerce(tokens[pos]))
                            pos += 1
                        pos += 1  # skip '}'
                        _set_key(result, key, items)
                    else:
                        # recursive block
                        child, pos = _parse_block(tokens, pos)
                        _set_key(result, key, child)
            else:
                _set_key(result, key, _coerce(tokens[pos]))
                pos += 1
        else:
            # bare token without '=' — skip (malformed or operator we don't handle)
            pos += 1

    return result, pos


class ClausewitzTextParser:
    """Full recursive parser for EU4 Clausewitz text format.

    Supports: scalars (int/float/bool/date/str), nested blocks, scalar lists,
    repeated keys (→ list), empty blocks, full-line and inline comments.
    """

    def parse_text(self, text: str) -> dict[str, Any]:
        """Parse a Clausewitz-format string and return a nested dict."""
        tokens = _tokenize(text)
        # Wrap in virtual braces so _parse_block handles everything uniformly.
        # Append a sentinel '}' so _parse_block returns at the right position.
        tokens.append('}')
        result, _ = _parse_block(tokens, 0)
        return result

    def parse_file(self, path: Path) -> dict[str, Any]:
        """Read a .eu4 text file and return a parsed dict."""
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("ClausewitzTextParser: cannot read %s: %s", path, exc)
            return {}
        return self.parse_text(text)


# ─────────────────────────────────────────────────────────────────────────────
# Legacy PoC parser (M1/M2) — kept for EU4RulesLoader backward compat
# ─────────────────────────────────────────────────────────────────────────────

class _LegacyClausewitzParser:
    """Minimal flat key-value parser (M1 PoC). Use ClausewitzTextParser for M3+."""

    def parse_file(self, path: Path) -> dict[str, str]:
        parsed: dict[str, str] = {}
        if not path.exists():
            return parsed
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            logger.warning("Could not read file %s: %s", path, exc)
            return parsed
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line in ("{", "}"):
                continue
            match = _PAIR.match(line)
            if not match:
                continue
            key = match.group("key").strip()
            raw_value = match.group("value").strip()
            if raw_value.startswith('"') and raw_value.endswith('"') and len(raw_value) >= 2:
                value = raw_value[1:-1]
            else:
                value = raw_value.split("#", 1)[0].strip()
            parsed[key] = value
        return parsed


# Deprecated alias — do not use in new code
ClausewitzParser = _LegacyClausewitzParser


# ─────────────────────────────────────────────────────────────────────────────
# EU4RulesLoader
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class RulesIndex:
    units: dict[str, dict[str, Any]] = field(default_factory=dict)
    ideas: dict[str, dict[str, Any]] = field(default_factory=dict)
    modifiers: dict[str, dict[str, Any]] = field(default_factory=dict)


class EU4RulesLoader:
    """Loads EU4 rules from install directory, merging mod overrides.

    Mod paths are applied in order: later entries override earlier ones.
    Install directory files are loaded first; mods override on a per-file basis.
    """

    def __init__(self, install_path: Path, mod_paths: list[Path] | None = None) -> None:
        self.install_path = install_path
        self.mod_paths = mod_paths or []
        self.parser = ClausewitzTextParser()

    def load_rules_index(self) -> RulesIndex:
        index = RulesIndex()
        self._load_folder(self.install_path / "common" / "units", index.units)
        self._load_folder(self.install_path / "common" / "ideas", index.ideas)
        self._load_folder(self.install_path / "common" / "event_modifiers", index.modifiers)
        for mod_path in self.mod_paths:
            self._load_folder(mod_path / "common" / "units", index.units)
            self._load_folder(mod_path / "common" / "ideas", index.ideas)
            self._load_folder(mod_path / "common" / "event_modifiers", index.modifiers)
        return index

    def _load_folder(self, folder: Path, target: dict[str, dict[str, Any]]) -> None:
        if not folder.exists():
            return
        for file in folder.glob("*.txt"):
            if file.stem in target:
                logger.debug("Mod override: '%s' replaces existing entry for '%s'", file, file.stem)
            target[file.stem] = self.parser.parse_file(file)
