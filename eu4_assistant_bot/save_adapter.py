"""Lightweight adapter for key=value save extracts.

Reads a simple ``key=value`` text file (one pair per line) and builds a
:class:`~eu4_assistant_bot.models.GameSnapshot`.  This is the M1/M2 bridge
format; real save files are handled by :mod:`save_unzipper` + :mod:`parser`.
"""

from __future__ import annotations

from pathlib import Path

from .models import EconomyState, GameSnapshot, MilitaryState, RiskState


class SaveAdapterError(Exception):
    """Raised when a save extract cannot be read or parsed."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class SaveSnapshotAdapter:
    """Lightweight adapter for key/value save extracts.

    Expected format (one key per line):
        timestamp=2026-01-01T00:00:00+00:00
        country=POR
        treasury=120
        income=12
        expenses=8
        debt=40
        force_limit=30
        manpower=15000
        coalition=0.35
        rebels=0.12
    """

    def read_save_extract(self, source: Path) -> GameSnapshot:
        try:
            content = source.read_text(encoding="utf-8")
        except OSError as exc:
            raise SaveAdapterError(f"Unable to read save extract: {source}") from exc

        payload: dict[str, str] = {}
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", maxsplit=1)
            payload[key.strip()] = value.strip()

        if "timestamp" not in payload:
            raise SaveAdapterError("Invalid save extract: missing required field 'timestamp'.")

        # Note: this M1/M2 legacy format only captures economy/military/risk.
        # War status, diplomacy, tech, ideas, trade nodes and provinces are not
        # present in key=value extracts and will default to safe empty values.
        # Real save files should be parsed via SaveUnzipper + StateExtractor.
        return GameSnapshot(
            timestamp=payload["timestamp"],
            country=payload.get("country", "UNK"),
            economy=EconomyState(
                treasury=self._to_float(payload.get("treasury"), default=0.0, field_name="treasury"),
                income=self._to_float(payload.get("income"), default=0.0, field_name="income"),
                expenses=self._to_float(payload.get("expenses"), default=0.0, field_name="expenses"),
                debt=self._to_float(payload.get("debt"), default=0.0, field_name="debt"),
            ),
            military=MilitaryState(
                force_limit=self._to_int(payload.get("force_limit"), default=0, field_name="force_limit"),
                manpower=self._to_int(payload.get("manpower"), default=0, field_name="manpower"),
            ),
            risk=RiskState(
                coalition=self._to_float(payload.get("coalition"), default=0.0, field_name="coalition"),
                rebels=self._to_float(payload.get("rebels"), default=0.0, field_name="rebels"),
            ),
        )

    @staticmethod
    def _to_float(raw: str | None, default: float, field_name: str = "") -> float:
        if raw is None or raw.strip() == "":
            return default
        try:
            return float(raw.strip())
        except ValueError as exc:
            raise SaveAdapterError(
                f"Invalid numeric value in save extract for field '{field_name}': '{raw}'"
            ) from exc

    @staticmethod
    def _to_int(raw: str | None, default: int, field_name: str = "") -> int:
        if raw is None or raw.strip() == "":
            return default
        try:
            return int(raw.strip())
        except ValueError as exc:
            raise SaveAdapterError(
                f"Invalid integer value in save extract for field '{field_name}': '{raw}'"
            ) from exc
