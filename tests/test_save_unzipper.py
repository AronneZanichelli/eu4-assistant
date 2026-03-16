"""Tests for SaveUnzipper (ZIP and plain-text saves)."""

import zipfile
from pathlib import Path
import pytest
from eu4_assistant_bot.save_unzipper import SaveFormatError, SaveUnzipper


def test_extract_from_valid_zip(sample_save_zip):
    text = SaveUnzipper().extract_gamestate(sample_save_zip)
    assert "date" in text
    assert "POR" in text


def test_extract_from_plain_text(tmp_path):
    p = tmp_path / "save.eu4"
    p.write_text('date = 1444.11.11\nplayer = "ENG"\n', encoding="utf-8")
    text = SaveUnzipper().extract_gamestate(p)
    assert "1444.11.11" in text


def test_raises_on_missing_file(tmp_path):
    with pytest.raises(SaveFormatError, match="not found"):
        SaveUnzipper().extract_gamestate(tmp_path / "missing.eu4")


def test_raises_on_zip_without_gamestate(tmp_path):
    p = tmp_path / "nogamestate.eu4"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("meta", "date = 1444.11.11\n")
    with pytest.raises(SaveFormatError, match="gamestate"):
        SaveUnzipper().extract_gamestate(p)


def test_raises_on_corrupted_file(tmp_path):
    p = tmp_path / "corrupt.eu4"
    p.write_bytes(b"PK\x00corrupted garbage \xff\xfe")
    with pytest.raises(SaveFormatError, match="[Cc]orrupted"):
        SaveUnzipper().extract_gamestate(p)


def test_extract_uses_gamestate_over_other_entries(tmp_path):
    """When both 'meta' and 'gamestate' exist, 'gamestate' must be returned."""
    p = tmp_path / "full.eu4"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("meta", "meta content")
        zf.writestr("gamestate", "gamestate content")
        zf.writestr("ai", "ai content")
    text = SaveUnzipper().extract_gamestate(p)
    assert text == "gamestate content"
