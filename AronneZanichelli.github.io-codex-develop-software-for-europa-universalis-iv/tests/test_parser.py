from pathlib import Path

from eu4_assistant_bot.parser import ClausewitzParser, EU4RulesLoader


def test_clausewitz_parser_reads_key_values(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text('discipline = 0.05\n# comment\nname = "Infantry"\n')

    parsed = ClausewitzParser().parse_file(sample)

    assert parsed["discipline"] == "0.05"
    assert parsed["name"] == "Infantry"


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
