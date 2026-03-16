"""Clausewitz parse-tree to typed GameSnapshot extractor.

:class:`StateExtractor` walks the raw ``dict`` produced by
:class:`~eu4_assistant_bot.parser.ClausewitzTextParser` and builds a fully
typed :class:`~eu4_assistant_bot.models.GameSnapshot`.  Every field access
is defensive: missing or malformed values fall back to safe defaults.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .models import (
    ArmyState,
    ColonialState,
    DiplomacyState,
    EconomyState,
    GameSnapshot,
    IdeasState,
    MilitaryState,
    RiskState,
    TechState,
)

logger = logging.getLogger(__name__)


class StateExtractor:
    """Converts a raw Clausewitz parse tree into a typed GameSnapshot.

    All field access is defensive: missing or malformed values fall back to
    safe defaults rather than raising exceptions.  This is intentional — EU4
    save files vary across DLC combinations and game versions.
    """

    def extract(self, tree: dict[str, Any]) -> GameSnapshot:
        """Extract a GameSnapshot from a parsed Clausewitz tree.

        Args:
            tree: Output of ClausewitzTextParser.parse_text() or parse_file().

        Returns:
            A fully populated GameSnapshot with safe defaults for any missing fields.
        """
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        country = self._str(tree.get("player"), default="UNK")
        eu4_date = self._str(tree.get("date"), default="")

        # Top-level scalars
        stability  = self._int(tree.get("stability"),  default=0)
        prestige   = self._float(tree.get("prestige"),  default=0.0)
        legitimacy = self._float(
            self._dig(tree, "countries", country, "legitimacy"),
            default=100.0,
        )

        economy  = self._extract_economy(tree, country)
        military = self._extract_military(tree, country)
        diplomacy = self._extract_diplomacy(tree, country)
        colonial  = self._extract_colonial(tree, country)
        risk      = self._extract_risk(tree, country)
        tech      = self._extract_tech(tree, country)
        ideas     = self._extract_ideas(tree, country)

        return GameSnapshot(
            timestamp=timestamp,
            country=country,
            eu4_date=eu4_date,
            stability=stability,
            prestige=prestige,
            legitimacy=legitimacy,
            economy=economy,
            military=military,
            diplomacy=diplomacy,
            colonial=colonial,
            risk=risk,
            tech=tech,
            ideas=ideas,
        )

    # ── Sub-extractors ────────────────────────────────────────────────────────

    def _extract_economy(self, tree: dict[str, Any], country: str) -> EconomyState:
        c = self._country_block(tree, country)
        return EconomyState(
            treasury=self._float(c.get("treasury"),    default=0.0),
            income=self._float(c.get("income"),        default=0.0),
            expenses=self._float(c.get("expenses"),    default=0.0),
            debt=self._float(c.get("loan_size"),       default=0.0),
        )

    def _extract_military(self, tree: dict[str, Any], country: str) -> MilitaryState:
        c = self._country_block(tree, country)
        armies_raw = c.get("army", [])
        if isinstance(armies_raw, dict):
            armies_raw = [armies_raw]
        armies: list[ArmyState] = []
        for a in armies_raw:
            if not isinstance(a, dict):
                continue
            armies.append(ArmyState(
                id=self._str(a.get("id"), default=""),
                name=self._str(a.get("name"), default=""),
                location=self._int(a.get("location"), default=0),
                strength=self._int(a.get("strength"), default=0),
                composition={},
            ))
        return MilitaryState(
            force_limit=self._int(c.get("land_forcelimit"), default=0),
            manpower=self._int(
                self._float(c.get("manpower"), default=0.0) * 1000,
                default=0,
            ),
            armies=armies,
        )

    def _extract_diplomacy(self, tree: dict[str, Any], country: str) -> DiplomacyState:
        c = self._country_block(tree, country)
        allies_raw = c.get("alliance", [])
        if isinstance(allies_raw, str):
            allies_raw = [allies_raw]
        elif not isinstance(allies_raw, list):
            allies_raw = []
        alliances = [str(a) for a in allies_raw]

        truce_raw = c.get("truce", [])
        if isinstance(truce_raw, dict):
            truce_raw = [truce_raw]
        elif not isinstance(truce_raw, list):
            truce_raw = []

        # Count active wars involving the player country
        active_wars = self._count_active_wars(tree, country)

        return DiplomacyState(
            truces=truce_raw,
            alliances=alliances,
            ae_map={},
            active_wars=active_wars,
        )

    def _extract_colonial(self, tree: dict[str, Any], country: str) -> ColonialState:
        c = self._country_block(tree, country)
        colonists = c.get("colonists", 0)
        if isinstance(colonists, list):
            colonists = len(colonists)
        return ColonialState(
            colonists_free=self._int(colonists, default=0),
            active_colonies=[],
        )

    def _extract_risk(self, tree: dict[str, Any], country: str) -> RiskState:
        c = self._country_block(tree, country)
        # rebel_faction risk: count factions
        rebels_raw = c.get("rebel_faction", [])
        if isinstance(rebels_raw, dict):
            rebels_raw = [rebels_raw]
        rebel_risk = min(len(rebels_raw) * 0.2, 1.0) if isinstance(rebels_raw, list) else 0.0
        # overextension → coalition proxy
        overext = self._float(c.get("overextension_percentage"), default=0.0)
        return RiskState(
            coalition=min(overext / 100.0, 1.0),
            rebels=rebel_risk,
        )

    def _extract_tech(self, tree: dict[str, Any], country: str) -> TechState:
        c = self._country_block(tree, country)
        tech_block = c.get("technology", {})
        if not isinstance(tech_block, dict):
            tech_block = {}
        return TechState(
            adm_tech=self._int(tech_block.get("adm_tech"), default=0),
            dip_tech=self._int(tech_block.get("dip_tech"), default=0),
            mil_tech=self._int(tech_block.get("mil_tech"), default=0),
            adm_points=self._int(c.get("adm_power"), default=0),
            dip_points=self._int(c.get("dip_power"), default=0),
            mil_points=self._int(c.get("mil_power"), default=0),
        )

    def _extract_ideas(self, tree: dict[str, Any], country: str) -> IdeasState:
        c = self._country_block(tree, country)
        ideas_block = c.get("active_idea_groups", {})
        if not isinstance(ideas_block, dict):
            ideas_block = {}
        completed: list[str] = []
        current_group = ""
        ideas_in_current = 0
        for group_name, count in ideas_block.items():
            n = self._int(count, default=0)
            if n >= 7:
                completed.append(group_name)
            else:
                current_group = group_name
                ideas_in_current = n
        return IdeasState(
            completed_groups=completed,
            current_group=current_group,
            ideas_in_current_group=ideas_in_current,
            free_policies=self._int(c.get("free_policies"), default=0),
        )

    # ── War detection ────────────────────────────────────────────────────────

    def _count_active_wars(self, tree: dict[str, Any], country: str) -> int:
        """Count top-level ``active_war`` entries involving *country*.

        EU4 stores wars at the tree root as ``active_war = { ... }`` blocks.
        Each block has ``participants`` containing country tags.  We count
        how many such blocks reference the player country.
        """
        wars_raw = tree.get("active_war", [])
        if isinstance(wars_raw, dict):
            wars_raw = [wars_raw]
        if not isinstance(wars_raw, list):
            return 0
        count = 0
        for war in wars_raw:
            if not isinstance(war, dict):
                continue
            # Check participants lists (attacker/defender)
            for side in ("participants", "attacker", "defender",
                         "original_attacker", "original_defender"):
                val = war.get(side, "")
                if isinstance(val, str) and val == country:
                    count += 1
                    break
                if isinstance(val, list) and country in val:
                    count += 1
                    break
                if isinstance(val, dict) and country in val.values():
                    count += 1
                    break
        return count

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _country_block(self, tree: dict[str, Any], country: str) -> dict[str, Any]:
        """Return the country sub-block, or empty dict if not found."""
        countries = tree.get("countries", {})
        if not isinstance(countries, dict):
            return {}
        block = countries.get(country, {})
        return block if isinstance(block, dict) else {}

    @staticmethod
    def _dig(tree: dict[str, Any], *keys: str) -> Any:
        """Navigate nested dicts safely; returns None if any key is missing."""
        node: Any = tree
        for key in keys:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

    @staticmethod
    def _str(value: Any, default: str = "") -> str:
        if value is None:
            return default
        return str(value)

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _int(value: Any, default: int = 0) -> int:
        if value is None:
            return default
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default
