from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
import re


# Key-value pair regex: dash placed at end of char class to avoid ambiguity
_PAIR = re.compile(r'(?P<key>[A-Za-z0-9_.\\-]+)\s*=\s*(?P<value>.+)')

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RulesIndex:
    units: dict[str, dict[str, str]] = field(default_factory=dict)
    ideas: dict[str, dict[str, str]] = field(default_factory=dict)
    modifiers: dict[str, dict[str, str]] = field(default_factory=dict)


class ClausewitzParser:
    """Minimal parser PoC for simple key-value blocks.

    Notes:
    - This is intentionally lightweight for M1/M2.
    - Full EU4 grammar support (recursive blocks, lists) will be added in M3
      via ClausewitzTextParser.
    """

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
            # Strip surrounding quotes if present
            if raw_value.startswith('"') and raw_value.endswith('"') and len(raw_value) >= 2:
                value = raw_value[1:-1]
            else:
                # Remove inline comment (naive but effective for PoC flat files)
                value = raw_value.split("#", 1)[0].strip()
            parsed[key] = value
        return parsed


class EU4RulesLoader:
    """Loads EU4 rules from install directory, merging mod overrides.

    Mod paths are applied in order: later entries override earlier ones.
    Install directory files are loaded first; mods override on a per-file basis.
    """

    def __init__(self, install_path: Path, mod_paths: list[Path] | None = None) -> None:
        self.install_path = install_path
        self.mod_paths = mod_paths or []
        self.parser = ClausewitzParser()

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

    def _load_folder(self, folder: Path, target: dict[str, dict[str, str]]) -> None:
        if not folder.exists():
            return
        for file in folder.glob("*.txt"):
            if file.stem in target:
                logger.debug("Mod override: '%s' replaces existing entry for '%s'", file, file.stem)
            target[file.stem] = self.parser.parse_file(file)
