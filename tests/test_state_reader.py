from pathlib import Path

import pytest

from eu4_assistant_bot.state_reader import SnapshotReadError, SnapshotReader


def test_read_json_snapshot(tmp_path: Path) -> None:
    sample = tmp_path / "snapshot.json"
    sample.write_text(
        """
{
  "timestamp": "2026-01-01T00:00:00+00:00",
  "country": "POR",
  "economy": {"treasury": 100, "income": 9, "expenses": 6, "debt": 0},
  "military": {"force_limit": 20, "manpower": 13000, "armies": []},
  "diplomacy": {"truces": [], "alliances": ["ENG"], "ae_map": {}},
  "colonial": {"colonists_free": 1, "active_colonies": []},
  "risk": {"coalition": 0.2, "rebels": 0.1}
}
""".strip()
    )

    out = SnapshotReader().read_json_snapshot(sample)

    assert out.country == "POR"
    assert out.economy.income == 9
    assert out.colonial.colonists_free == 1


def test_read_json_snapshot_tolerates_null_sections(tmp_path: Path) -> None:
    """Regression test for P1 bug: null or non-mapping nested sections must not raise TypeError."""
    sample = tmp_path / "snapshot-nulls.json"
    sample.write_text(
        '{"timestamp": "2026-01-01T00:00:00+00:00", "country": "POR", "economy": null, "military": []}'
    )

    out = SnapshotReader().read_json_snapshot(sample)

    assert out.country == "POR"
    assert out.economy.treasury == 0.0
    assert out.military.manpower == 0


def test_read_json_snapshot_raises_on_missing_timestamp(tmp_path: Path) -> None:
    sample = tmp_path / "snapshot-invalid.json"
    sample.write_text('{"country": "POR"}')

    with pytest.raises(SnapshotReadError, match="missing required field 'timestamp'"):
        SnapshotReader().read_json_snapshot(sample)
