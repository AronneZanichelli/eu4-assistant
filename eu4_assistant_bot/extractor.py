"""Clausewitz parse-tree to typed GameSnapshot extractor."""

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
    ProvinceState,
    RiskState,
    TechState,
    TradeNodeState,
)

logger = logging.getLogger(__name__)


class StateExtractor:
    """Converts a raw Clausewitz parse tree into a typed GameSnapshot.

    All field access is defensive: missing or malformed values fall back to
    safe defaults rather than raising exceptions.
    """

    def extract(self, tree: dict[str, Any]) -> GameSnapshot:
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        country = self._str(tree.get("player"), default="UNK")
        eu4_date = self._str(tree.get("date"), default="")
        stability  = self._int(tree.get("stability"),  default=0)
        prestige   = self._float(tree.get("prestige"),  default=0.0)
        legitimacy = self._float(
            self._dig(tree, "countries", country, "legitimacy"),
            default=100.0,
        )
        economy     = self._extract_economy(tree, country)
        military    = self._extract_military(tree, country)
        diplomacy   = self._extract_diplomacy(tree, country)
        colonial    = self._extract_colonial(tree, country)
        risk        = self._extract_risk(tree, country)
        tech        = self._extract_tech(tree, country)
        ideas       = self._extract_ideas(tree, country)
        trade_nodes = self._extract_trade_nodes(tree, country)
        provinces   = self._extract_provinces(tree, country)
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
            trade_nodes=trade_nodes,
            provinces=provinces,
        )

    def _extract_economy(self, tree: dict[str, Any], country: str) -> EconomyState:
        c = self._country_block(tree, country)
        merchants_raw = c.get("merchant", [])
        if isinstance(merchants_raw, dict):
            merchants_raw = [merchants_raw]
        deployed = len(merchants_raw) if isinstance(merchants_raw, list) else 0
        return EconomyState(
            treasury=self._float(c.get("treasury"), default=0.0),
            income=self._float(c.get("income"), default=0.0),
            expenses=self._float(c.get("expenses"), default=0.0),
            debt=self._float(c.get("loan_size"), default=0.0),
            merchants_deployed=deployed,
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
            composition = self._parse_composition(a)
            armies.append(ArmyState(
                id=self._str(a.get("id"), default=""),
                name=self._str(a.get("name"), default=""),
                location=self._int(a.get("location"), default=0),
                strength=self._int(a.get("strength"), default=0),
                composition=composition,
            ))
        return MilitaryState(
            force_limit=self._int(c.get("land_forcelimit"), default=0),
            manpower=self._int(
                self._float(c.get("manpower"), default=0.0) * 1000,
                default=0,
            ),
            armies=armies,
        )

    def _parse_composition(self, army: dict[str, Any]) -> dict[str, int]:
        """Extract unit composition from army block."""
        comp: dict[str, int] = {}
        regiment_raw = army.get("regiment", [])
        if isinstance(regiment_raw, dict):
            regiment_raw = [regiment_raw]
        if isinstance(regiment_raw, list):
            for reg in regiment_raw:
                if not isinstance(reg, dict):
                    continue
                utype = self._str(reg.get("type"), default="unknown")
                comp[utype] = comp.get(utype, 0) + 1
        return comp

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

        active_wars = self._int(c.get("num_of_war_with_us"), default=0)

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
        rebels_raw = c.get("rebel_faction", [])
        if isinstance(rebels_raw, dict):
            rebels_raw = [rebels_raw]
        rebel_risk = min(len(rebels_raw) * 0.2, 1.0) if isinstance(rebels_raw, list) else 0.0
        overext = self._float(c.get("overextension_percentage"), default=0.0)
        ae_max = self._float(c.get("max_aggressive_expansion"), default=0.0)
        return RiskState(
            coalition=min(overext / 100.0, 1.0),
            rebels=rebel_risk,
            ae_max=ae_max,
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

    def _extract_trade_nodes(self, tree: dict[str, Any], country: str) -> list[TradeNodeState]:
        """Extract trade node data for the player country."""
        nodes: list[TradeNodeState] = []
        trade_raw = tree.get("trade", {})
        if not isinstance(trade_raw, dict):
            return nodes
        node_raw = trade_raw.get("node", [])
        if isinstance(node_raw, dict):
            node_raw = [node_raw]
        if not isinstance(node_raw, list):
            return nodes
        for node in node_raw:
            if not isinstance(node, dict):
                continue
            node_id = self._str(node.get("definitions"), default="")
            our_power = 0.0
            merchants = 0
            for country_data in node.get("country", []) if isinstance(node.get("country"), list) else [node.get("country", {})]:
                if isinstance(country_data, dict) and country_data.get("country") == country:
                    our_power = self._float(country_data.get("power"), default=0.0)
                    merchants = self._int(country_data.get("num_merchants"), default=0)
            total_value = self._float(node.get("local_value"), default=0.0)
            nodes.append(TradeNodeState(
                id=node_id,
                our_power=our_power,
                total_value=total_value,
                merchants=merchants,
            ))
        return nodes

    def _extract_provinces(self, tree: dict[str, Any], country: str) -> list[ProvinceState]:
        """Extract province states owned by the player country."""
        provinces: list[ProvinceState] = []
        provinces_raw = tree.get("provinces", {})
        if not isinstance(provinces_raw, dict):
            return provinces
        for province_id_str, prov_data in provinces_raw.items():
            if not isinstance(prov_data, dict):
                continue
            if prov_data.get("owner") != country:
                continue
            provinces.append(ProvinceState(
                province_id=abs(self._int(province_id_str, default=0)),
                name=self._str(prov_data.get("name"), default=""),
                owner=country,
                development=self._float(prov_data.get("base_tax", 0), default=0.0) +
                             self._float(prov_data.get("base_production", 0), default=0.0) +
                             self._float(prov_data.get("base_manpower", 0), default=0.0),
                unrest=self._float(prov_data.get("unrest"), default=0.0),
                trade_good=self._str(prov_data.get("trade_goods"), default=""),
            ))
        return provinces

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _country_block(self, tree: dict[str, Any], country: str) -> dict[str, Any]:
        countries = tree.get("countries", {})
        if not isinstance(countries, dict):
            return {}
        block = countries.get(country, {})
        return block if isinstance(block, dict) else {}

    @staticmethod
    def _dig(tree: dict[str, Any], *keys: str) -> Any:
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
