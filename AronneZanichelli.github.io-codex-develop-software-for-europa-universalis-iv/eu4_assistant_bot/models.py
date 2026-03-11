from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any


@dataclass(slots=True)
class EconomyState:
    treasury: float = 0.0
    income: float = 0.0
    expenses: float = 0.0
    debt: float = 0.0


@dataclass(slots=True)
class MilitaryState:
    force_limit: int = 0
    manpower: int = 0
    armies: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class DiplomacyState:
    truces: list[dict[str, Any]] = field(default_factory=list)
    alliances: list[str] = field(default_factory=list)
    ae_map: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class ColonialState:
    colonists_free: int = 0
    active_colonies: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class RiskState:
    coalition: float = 0.0
    rebels: float = 0.0


@dataclass(slots=True)
class GameSnapshot:
    timestamp: str
    country: str
    economy: EconomyState = field(default_factory=EconomyState)
    military: MilitaryState = field(default_factory=MilitaryState)
    diplomacy: DiplomacyState = field(default_factory=DiplomacyState)
    colonial: ColonialState = field(default_factory=ColonialState)
    risk: RiskState = field(default_factory=RiskState)

    @classmethod
    def empty(cls, country: str = "UNK") -> "GameSnapshot":
        now = datetime.now(tz=timezone.utc).isoformat()
        return cls(timestamp=now, country=country)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def save(self, output_path: Path) -> None:
        output_path.write_text(self.to_json(), encoding="utf-8")


@dataclass(slots=True)
class ActionPlan:
    id: str
    action_type: str
    priority: float
    confidence: float
    expected_outcome: dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = True
