"""Integration tests for the live watch pipeline (G1).

Exercises the path the ``--watch`` loop runs on every save —
``_save_to_snapshot`` = unzip -> parse -> extract — which C1 broke (a call to a
non-existent ``parse()`` method) and which no test covered. A regression back to
``.parse()`` makes these tests fail with AttributeError.
"""

import zipfile
from pathlib import Path

import pytest

from eu4_assistant_bot.extractor import StateExtractor
from eu4_assistant_bot.main import _save_to_snapshot
from eu4_assistant_bot.parser import ClausewitzTextParser
from eu4_assistant_bot.save_unzipper import SaveFormatError


def _assert_populated_por(snap) -> None:
    """Fields that must survive the full parse -> extract pipeline non-empty."""
    assert snap.country == "POR"
    assert snap.eu4_date == "1460.06.01"
    assert snap.economy.treasury == pytest.approx(120.5)
    assert snap.military.manpower == 22000
    assert snap.tech.mil_tech == 4


def test_save_to_snapshot_plain_text(fixtures_dir: Path):
    """A plain-text .eu4 save flows end-to-end to a populated snapshot."""
    snap = _save_to_snapshot(fixtures_dir / "sample_nested.eu4.txt")
    _assert_populated_por(snap)


def test_save_to_snapshot_zip(tmp_path: Path, fixtures_dir: Path):
    """A real ZIP .eu4 save (gamestate entry) flows end-to-end (ZIP path)."""
    gamestate = (fixtures_dir / "sample_nested.eu4.txt").read_text(encoding="utf-8")
    save = tmp_path / "autosave.eu4"
    with zipfile.ZipFile(save, "w") as zf:
        zf.writestr("meta", "date = 1460.06.01\n")
        zf.writestr("gamestate", gamestate)
        zf.writestr("ai", "")
    snap = _save_to_snapshot(save)
    _assert_populated_por(snap)


def test_parser_output_feeds_extractor_non_empty(fixtures_dir: Path):
    """ClausewitzTextParser output populates StateExtractor (no silent empties)."""
    text = (fixtures_dir / "sample_nested.eu4.txt").read_text(encoding="utf-8")
    tree = ClausewitzTextParser().parse_text(text)
    snap = StateExtractor().extract(tree)
    _assert_populated_por(snap)


def test_save_to_snapshot_missing_file_raises(tmp_path: Path):
    """A missing save raises SaveFormatError (the 'bad save' branch of _process_save)."""
    with pytest.raises(SaveFormatError):
        _save_to_snapshot(tmp_path / "does_not_exist.eu4")


def test_save_to_snapshot_corrupt_zip_raises(tmp_path: Path):
    """ZIP magic but corrupt content raises SaveFormatError, not a bare exception."""
    bad = tmp_path / "corrupt.eu4"
    bad.write_bytes(b"PK\x03\x04 not a real zip")
    with pytest.raises(SaveFormatError):
        _save_to_snapshot(bad)
