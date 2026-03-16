from __future__ import annotations

from pathlib import Path
import json

from .models import (
    ColonialState,
    DiplomacyState,
    EconomyState,
    GameSnapshot,
    IdeasState,
    MilitaryState,
    RiskState,
    TechState,
)


class SnapshotReadError(Exception):
    """Raised when a snapshot cannot be read or is malformed."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
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
            eu4_date=payload.get("eu4_date", ""),
            stability=payload.get("stability", 0),
            prestige=payload.get("prestige", 0.0),
            legitimacy=payload.get("legitimacy", 100.0),
            economy=EconomyState(**_safe_dict("economy")),
            military=MilitaryState(**_safe_dict("military")),
            diplomacy=DiplomacyState(**_safe_dict("diplomacy")),
            colonial=ColonialState(**_safe_dict("colonial")),
            risk=RiskState(**_safe_dict("risk")),
            tech=TechState(**_safe_dict("tech")),
            ideas=IdeasState(**_safe_dict("ideas")),
        )
