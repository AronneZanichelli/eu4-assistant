from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import EconomyState, GameSnapshot, MilitaryState, RiskState


@dataclass(slots=True)
class SaveAdapterError(Exception):
    message: str

    def __str__(self) -> str:  # pragma: no cover
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
            striped = line.strip()
            if not striped or striped.startswith("#"):
                continue
            if "=" not in striped:
                continue
            key, value = striped.split("=", maxsplit=1)
            payload[key.strip()] = value.strip()

        if "timestamp" not in payload:
            raise SaveAdapterError("Invalid save extract: missing required field 'timestamp'.")

        return GameSnapshot(
            timestamp=payload["timestamp"],
            country=payload.get("country", "UNK"),
            economy=EconomyState(
                treasury=self._to_float(payload.get("treasury"), default=0.0),
                income=self._to_float(payload.get("income"), default=0.0),
                expenses=self._to_float(payload.get("expenses"), default=0.0),
                debt=self._to_float(payload.get("debt"), default=0.0),
            ),
            military=MilitaryState(
                force_limit=self._to_int(payload.get("force_limit"), default=0),
                manpower=self._to_int(payload.get("manpower"), default=0),
            ),
            risk=RiskState(
                coalition=self._to_float(payload.get("coalition"), default=0.0),
                rebels=self._to_float(payload.get("rebels"), default=0.0),
            ),
        )

    @staticmethod
    def _to_float(raw: str | None, default: float) -> float:
        if raw is None:
            return default
        try:
            return float(raw)
        except ValueError as exc:
            raise SaveAdapterError(f"Invalid numeric value in save extract: '{raw}'") from exc

    @staticmethod
    def _to_int(raw: str | None, default: int) -> int:
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError as exc:
            raise SaveAdapterError(f"Invalid integer value in save extract: '{raw}'") from exc
