from pathlib import Path

import pytest

from eu4_assistant_bot.parser import ClausewitzParser, EU4RulesLoader


def test_clausewitz_parser_reads_key_values(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text('discipline = 0.05\n# comment\nname = "Infantry"\n')

    parsed = ClausewitzParser().parse_file(sample)

    assert parsed["discipline"] == "0.05"
    assert parsed["name"] == "Infantry"


def test_clausewitz_parser_strips_inline_comments(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("manpower = 12000 # this is a comment\n")

    parsed = ClausewitzParser().parse_file(sample)

    assert parsed["manpower"] == "12000"


def test_clausewitz_parser_quoted_value_with_hash(tmp_path: Path) -> None:
    """Quoted values containing # should be preserved as-is."""
    sample = tmp_path / "sample.txt"
    sample.write_text('color = "#ff0000"\n')

    parsed = ClausewitzParser().parse_file(sample)

    assert parsed["color"] == "#ff0000"


def test_clausewitz_parser_skips_braces_and_comments(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("{\n# full line comment\n}\nkey = val\n")

    parsed = ClausewitzParser().parse_file(sample)

    assert list(parsed.keys()) == ["key"]


def test_clausewitz_parser_returns_empty_for_missing_file(tmp_path: Path) -> None:
    parsed = ClausewitzParser().parse_file(tmp_path / "nonexistent.txt")
    assert parsed == {}


def test_rules_loader_merges_install_and_mod(tmp_path: Path) -> None:
    install = tmp_path / "eu4"
    mod = tmp_path / "modA"
    (install / "common" / "units").mkdir(parents=True)
    (mod / "common" / "units").mkdir(parents=True)

    (install / "common" / "units" / "western.txt").write_text("tech = western\n")
    (mod / "common" / "units" / "mod_unit.txt").write_text("tech = modded\n")

    idx = EU4RulesLoader(install, [mod]).load_rules_index()

    assert "western" in idx.units
    assert "mod_unit" in idx.units


def test_rules_loader_mod_overrides_install(tmp_path: Path) -> None:
    """Mod files override install files with the same stem."""
    install = tmp_path / "eu4"
    mod = tmp_path / "modA"
    (install / "common" / "units").mkdir(parents=True)
    (mod / "common" / "units").mkdir(parents=True)

    (install / "common" / "units" / "western.txt").write_text("maneuver = 1\n")
    (mod / "common" / "units" / "western.txt").write_text("maneuver = 3\n")

    idx = EU4RulesLoader(install, [mod]).load_rules_index()

    assert idx.units["western"]["maneuver"] == "3"
