from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from .models import (
    ColonialState,
    DiplomacyState,
    EconomyState,
    GameSnapshot,
    MilitaryState,
    RiskState,
)


@dataclass(slots=True)
class SnapshotReadError(Exception):
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial method
        return self.message


class SnapshotReader:
    """M2 state reader for normalized JSON snapshots (bridge for save/OCR adapters)."""

    def read_json_snapshot(self, source: Path) -> GameSnapshot:
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except OSError as exc:
            raise SnapshotReadError(f"Unable to read snapshot file: {source}") from exc
        except json.JSONDecodeError as exc:
            raise SnapshotReadError(f"Invalid JSON snapshot at {source}: {exc}") from exc

        if "timestamp" not in payload:
            raise SnapshotReadError("Invalid snapshot payload: missing required field 'timestamp'.")

        def _safe_dict(key: str) -> dict:
            """Return the nested mapping for *key*, or {} if it is missing/null/non-mapping."""
            value = payload.get(key)
            return value if isinstance(value, dict) else {}

        return GameSnapshot(
            timestamp=payload["timestamp"],
            country=payload.get("country", "UNK"),
            economy=EconomyState(**_safe_dict("economy")),
            military=MilitaryState(**_safe_dict("military")),
            diplomacy=DiplomacyState(**_safe_dict("diplomacy")),
            colonial=ColonialState(**_safe_dict("colonial")),
            risk=RiskState(**_safe_dict("risk")),
        )
