from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class EconomyState:
    treasury: float = 0.0
    income: float = 0.0
    expenses: float = 0.0
    debt: float = 0.0
    merchants_deployed: int = 0
    total_merchants: int = 0


@dataclass(slots=True)
class ArmyState:
    """Individual army unit state."""
    id: str = ""
    name: str = ""
    location: int = 0
    strength: int = 0
    composition: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class ProvinceState:
    """Province state for colonial and military logic."""
    province_id: int = 0
    name: str = ""
    owner: str = ""
    development: float = 0.0
    base_tax: float = 0.0
    unrest: float = 0.0
    trade_good: str = ""
    is_colony: bool = False
    colony_progress: int = 0  # 0–1000


@dataclass(slots=True)
class TradeNodeState:
    """Trade node state for economy logic."""
    id: str = ""
    our_power: float = 0.0
    total_value: float = 0.0
    merchants: int = 0


@dataclass(slots=True)
class WarState:
    """Active war state extracted from save."""
    war_name: str = ""
    attacker: str = ""          # lead attacker tag
    defender: str = ""          # lead defender tag
    our_side: str = ""          # "attacker" | "defender"
    war_score: float = 0.0     # -100 → +100
    start_date: str = ""


@dataclass(slots=True)
class BattleOdds:
    """Pre-engagement strength comparison."""
    our_strength: int = 0
    enemy_strength: int = 0
    our_combat_width_fill: float = 0.0   # 0.0–1.0+
    strength_ratio: float = 0.0          # our/enemy
    favorable: bool = False


@dataclass(slots=True)
class MilitaryState:
    force_limit: int = 0
    manpower: int = 0
    armies: list[ArmyState] = field(default_factory=list)
    wars: list[WarState] = field(default_factory=list)
    at_war: bool = False


@dataclass(slots=True)
class DiplomacyState:
    truces: list[dict[str, Any]] = field(default_factory=list)
    alliances: list[str] = field(default_factory=list)
    ae_map: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class ColonialState:
    colonists_free: int = 0
    total_colonists: int = 0
    active_colonies: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class RiskState:
    coalition: float = 0.0
    rebels: float = 0.0
    ae_max: float = 0.0


@dataclass(slots=True)
class TechState:
    """Administrative, diplomatic and military technology levels."""
    adm_tech: int = 0
    dip_tech: int = 0
    mil_tech: int = 0
    adm_points: int = 0   # monarch points available
    dip_points: int = 0
    mil_points: int = 0


@dataclass(slots=True)
class IdeasState:
    """Idea groups and free idea points."""
    completed_groups: list[str] = field(default_factory=list)
    current_group: str = ""          # group being unlocked (empty if none)
    ideas_in_current_group: int = 0  # ideas unlocked in current group (0–7)
    free_policies: int = 0           # unlocked policy slots


@dataclass(slots=True)
class GameSnapshot:
    timestamp: str
    country: str
    # M4 additions
    eu4_date: str = ""           # in-game date "YYYY.MM.DD"
    stability: int = 0           # -3 → +3
    prestige: float = 0.0
    legitimacy: float = 100.0
    # Sub-states
    economy: EconomyState = field(default_factory=EconomyState)
    military: MilitaryState = field(default_factory=MilitaryState)
    diplomacy: DiplomacyState = field(default_factory=DiplomacyState)
    colonial: ColonialState = field(default_factory=ColonialState)
    risk: RiskState = field(default_factory=RiskState)
    tech: TechState = field(default_factory=TechState)
    ideas: IdeasState = field(default_factory=IdeasState)
    trade_nodes: list[TradeNodeState] = field(default_factory=list)
    provinces: list[ProvinceState] = field(default_factory=list)

    @classmethod
    def empty(cls, country: str = "UNK") -> "GameSnapshot":
        now = datetime.now(tz=timezone.utc).isoformat()
        return cls(timestamp=now, country=country)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def save(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.to_json(), encoding="utf-8")


@dataclass(slots=True)
class ActionPlan:
    id: str
    action_type: str
    priority: float
    confidence: float
    expected_outcome: dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = True
