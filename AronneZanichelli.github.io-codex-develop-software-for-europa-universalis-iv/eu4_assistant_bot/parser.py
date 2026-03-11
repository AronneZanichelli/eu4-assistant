from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


_PAIR = re.compile(r"(?P<key>[A-Za-z0-9_\-.]+)\s*=\s*(?P<value>.+)")


@dataclass(slots=True)
class RulesIndex:
    units: dict[str, dict[str, str]] = field(default_factory=dict)
    ideas: dict[str, dict[str, str]] = field(default_factory=dict)
    modifiers: dict[str, dict[str, str]] = field(default_factory=dict)


class ClausewitzParser:
    """Minimal parser PoC for simple key-value blocks.

    Notes:
    - This is intentionally lightweight for M1.
    - Full EU4 grammar support will be expanded in M2/M3.
    """

    def parse_file(self, path: Path) -> dict[str, str]:
        parsed: dict[str, str] = {}
        if not path.exists():
            return parsed

        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line in ("{", "}"):
                continue
            match = _PAIR.match(line)
            if match:
                key = match.group("key").strip()
                value = match.group("value").strip().strip('"')
                parsed[key] = value
        return parsed


class EU4RulesLoader:
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
            target[file.stem] = self.parser.parse_file(file)
