from pathlib import Path
import pytest
from eu4_assistant_bot.parser import ClausewitzParser, ClausewitzTextParser, EU4RulesLoader


# ── ClausewitzTextParser — scalari ────────────────────────────────────────────

def test_parse_integer():
    result = ClausewitzTextParser().parse_text("adm_tech = 4")
    assert result["adm_tech"] == 4
    assert isinstance(result["adm_tech"], int)


def test_parse_float():
    result = ClausewitzTextParser().parse_text("treasury = 120.500")
    assert result["treasury"] == pytest.approx(120.5)
    assert isinstance(result["treasury"], float)


def test_parse_bool_yes_no():
    result = ClausewitzTextParser().parse_text("multi_player = no\nironman = yes")
    assert result["multi_player"] is False
    assert result["ironman"] is True


def test_parse_quoted_string():
    result = ClausewitzTextParser().parse_text('player = "POR"')
    assert result["player"] == "POR"


def test_parse_date_string():
    result = ClausewitzTextParser().parse_text("date = 1460.06.01")
    assert result["date"] == "1460.06.01"
    assert isinstance(result["date"], str)


# ── strutture ─────────────────────────────────────────────────────────────────

def test_parse_nested_block():
    text = 'countries = {\n    POR = {\n        treasury = 120\n    }\n}'
    result = ClausewitzTextParser().parse_text(text)
    assert result["countries"]["POR"]["treasury"] == 120


def test_parse_deep_nested_block():
    text = "a = { b = { c = { d = 42 } } }"
    result = ClausewitzTextParser().parse_text(text)
    assert result["a"]["b"]["c"]["d"] == 42


def test_parse_scalar_list():
    result = ClausewitzTextParser().parse_text("tags = { ENG FRA POR }")
    assert result["tags"] == ["ENG", "FRA", "POR"]


def test_parse_scalar_list_integers():
    result = ClausewitzTextParser().parse_text("ids = { 1 2 3 }")
    assert result["ids"] == [1, 2, 3]


def test_parse_repeated_key_becomes_list():
    text = 'army = { name = "First" }\narmy = { name = "Second" }'
    result = ClausewitzTextParser().parse_text(text)
    assert isinstance(result["army"], list)
    assert len(result["army"]) == 2
    assert result["army"][0]["name"] == "First"
    assert result["army"][1]["name"] == "Second"


def test_parse_empty_block():
    result = ClausewitzTextParser().parse_text("modifiers = { }")
    assert result["modifiers"] == []


# ── robustezza ────────────────────────────────────────────────────────────────

def test_parse_ignores_comments():
    result = ClausewitzTextParser().parse_text("# full line comment\nkey = val")
    assert "key" in result
    assert len(result) == 1


def test_parse_inline_comment():
    result = ClausewitzTextParser().parse_text("speed = 3 # fast")
    assert result["speed"] == 3


def test_parse_empty_string():
    result = ClausewitzTextParser().parse_text("")
    assert result == {}


def test_parse_only_comments():
    result = ClausewitzTextParser().parse_text("# comment\n# another")
    assert result == {}


def test_parse_non_ascii_values():
    result = ClausewitzTextParser().parse_text('name = "Álvaro de Bragança"')
    assert result["name"] == "Álvaro de Bragança"


# ── file ──────────────────────────────────────────────────────────────────────

def test_parse_file(fixtures_dir):
    path = fixtures_dir / "sample_nested.eu4.txt"
    result = ClausewitzTextParser().parse_file(path)
    assert result["date"] == "1460.06.01"
    assert result["player"] == "POR"
    assert isinstance(result["army"], list)
    assert len(result["army"]) == 2
    assert result["countries"]["POR"]["treasury"] == pytest.approx(120.5)


def test_parse_file_flat(fixtures_dir):
    path = fixtures_dir / "sample_flat.eu4.txt"
    result = ClausewitzTextParser().parse_file(path)
    assert result["speed"] == 3
    assert result["multi_player"] is False


def test_parse_file_missing_returns_empty(tmp_path):
    result = ClausewitzTextParser().parse_file(tmp_path / "nonexistent.txt")
    assert result == {}


# ── backward compat: ClausewitzParser alias ───────────────────────────────────

def test_legacy_alias_still_works(tmp_path):
    f = tmp_path / "unit.txt"
    f.write_text('discipline = 0.05\nname = "Infantry"\n')
    result = ClausewitzParser().parse_file(f)
    assert result["discipline"] == "0.05"
    assert result["name"] == "Infantry"


# ── EU4RulesLoader ────────────────────────────────────────────────────────────

def test_rules_loader_merges_install_and_mod(tmp_path):
    install = tmp_path / "eu4"
    mod = tmp_path / "modA"
    (install / "common" / "units").mkdir(parents=True)
    (mod / "common" / "units").mkdir(parents=True)
    (install / "common" / "units" / "western.txt").write_text("tech = western\n")
    (mod / "common" / "units" / "mod_unit.txt").write_text("tech = modded\n")
    idx = EU4RulesLoader(install, [mod]).load_rules_index()
    assert "western" in idx.units
    assert "mod_unit" in idx.units


def test_rules_loader_mod_overrides_install(tmp_path):
    install = tmp_path / "eu4"
    mod = tmp_path / "modA"
    (install / "common" / "units").mkdir(parents=True)
    (mod / "common" / "units").mkdir(parents=True)
    (install / "common" / "units" / "western.txt").write_text("maneuver = 1\n")
    (mod / "common" / "units" / "western.txt").write_text("maneuver = 3\n")
    idx = EU4RulesLoader(install, [mod]).load_rules_index()
    assert idx.units["western"]["maneuver"] == "3"
