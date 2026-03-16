"""Tests for SaveSnapshotAdapter (key=value format)."""

from pathlib import Path

import pytest

from eu4_assistant_bot.save_adapter import SaveAdapterError, SaveSnapshotAdapter


def test_read_save_extract_maps_values(tmp_path: Path) -> None:
    save = tmp_path / "campaign.extract"
    save.write_text(
        "\n".join([
            "timestamp=2026-01-01T00:00:00+00:00",
            "country=POR",
            "treasury=123.4",
            "income=12",
            "expenses=7.5",
            "debt=50",
            "force_limit=28",
            "manpower=19000",
            "coalition=0.35",
            "rebels=0.22",
        ])
    )

    out = SaveSnapshotAdapter().read_save_extract(save)

    assert out.country == "POR"
    assert out.economy.treasury == 123.4
    assert out.military.force_limit == 28
    assert out.risk.rebels == 0.22


def test_read_save_extract_requires_timestamp(tmp_path: Path) -> None:
    save = tmp_path / "invalid.extract"
    save.write_text("country=POR\n")

    with pytest.raises(SaveAdapterError, match="missing required field 'timestamp'"):
        SaveSnapshotAdapter().read_save_extract(save)


def test_read_save_extract_empty_fields_use_default(tmp_path: Path) -> None:
    """Empty or missing numeric fields should return defaults, not raise."""
    save = tmp_path / "sparse.extract"
    save.write_text("timestamp=2026-01-01T00:00:00+00:00\ncountry=ENG\ntreasury=\n")

    out = SaveSnapshotAdapter().read_save_extract(save)

    assert out.economy.treasury == 0.0
    assert out.economy.income == 0.0
    assert out.military.force_limit == 0


def test_read_save_extract_whitespace_values_use_default(tmp_path: Path) -> None:
    """Fields with only whitespace should return defaults."""
    save = tmp_path / "ws.extract"
    save.write_text("timestamp=2026-01-01T00:00:00+00:00\nmanpower=   \n")

    out = SaveSnapshotAdapter().read_save_extract(save)

    assert out.military.manpower == 0


def test_read_save_extract_invalid_float_raises(tmp_path: Path) -> None:
    save = tmp_path / "bad.extract"
    save.write_text("timestamp=2026-01-01T00:00:00+00:00\ntreasury=not_a_number\n")

    with pytest.raises(SaveAdapterError, match="treasury"):
        SaveSnapshotAdapter().read_save_extract(save)


def test_read_save_extract_invalid_int_raises(tmp_path: Path) -> None:
    save = tmp_path / "bad.extract"
    save.write_text("timestamp=2026-01-01T00:00:00+00:00\nforce_limit=abc\n")

    with pytest.raises(SaveAdapterError, match="force_limit"):
        SaveSnapshotAdapter().read_save_extract(save)
