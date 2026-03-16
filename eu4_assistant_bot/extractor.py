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
    WarState,
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

    # ── Sub-extractors ────────────────────────────────────────────────────────

    def _extract_economy(self, tree: dict[str, Any], country: str) -> EconomyState:
        c = self._country_block(tree, country)
        # Count deployed and total merchants
        merchants_raw = c.get("merchant", [])
        if isinstance(merchants_raw, dict):
            merchants_raw = [merchants_raw]
        deployed = len(merchants_raw) if isinstance(merchants_raw, list) else 0
        total_merchants = self._int(c.get("num_of_merchants"), default=0)
        return EconomyState(
            treasury=self._float(c.get("treasury"),    default=0.0),
            income=self._float(c.get("income"),        default=0.0),
            expenses=self._float(c.get("expenses"),    default=0.0),
            debt=self._float(c.get("loan_size"),       default=0.0),
            merchants_deployed=deployed,
            total_merchants=total_merchants,
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
        wars = self._extract_wars(tree, country)
        return MilitaryState(
            force_limit=self._int(c.get("land_forcelimit"), default=0),
            manpower=self._int(
                self._float(c.get("manpower"), default=0.0) * 1000,
                default=0,
            ),
            armies=armies,
            wars=wars,
            at_war=len(wars) > 0,
        )

    @staticmethod
    def _parse_composition(army_block: dict[str, Any]) -> dict[str, int]:
        """Parse regiment list into infantry/cavalry/artillery counts."""
        regiments = army_block.get("regiment", [])
        if isinstance(regiments, dict):
            regiments = [regiments]
        composition: dict[str, int] = {"infantry": 0, "cavalry": 0, "artillery": 0}
        for reg in regiments:
            if not isinstance(reg, dict):
                continue
            unit_type = str(reg.get("type", "")).lower()
            for cat in ("infantry", "cavalry", "artillery"):
                if cat in unit_type:
                    composition[cat] += 1
                    break
        return composition

    def _extract_wars(self, tree: dict[str, Any], country: str) -> list[WarState]:
        """Extract active wars involving the player country."""
        wars_raw = tree.get("active_war", [])
        if isinstance(wars_raw, dict):
            wars_raw = [wars_raw]
        wars: list[WarState] = []
        for w in wars_raw:
            if not isinstance(w, dict):
                continue
            raw_atk = w.get("attacker", "")
            attacker = self._str(raw_atk.get("tag") if isinstance(raw_atk, dict) else raw_atk, default="")
            raw_def = w.get("defender", "")
            defender = self._str(raw_def.get("tag") if isinstance(raw_def, dict) else raw_def, default="")
            # Check participants lists for our country
            attackers = self._war_participants(w, "attackers")
            defenders = self._war_participants(w, "defenders")
            if country in attackers:
                our_side = "attacker"
            elif country in defenders:
                our_side = "defender"
            else:
                continue  # not our war
            wars.append(WarState(
                war_name=self._str(w.get("name"), default=""),
                attacker=attacker,
                defender=defender,
                our_side=our_side,
                war_score=self._float(w.get("war_score"), default=0.0),
                start_date=self._str(w.get("start_date"), default=""),
            ))
        return wars

    @staticmethod
    def _war_participants(war_block: dict[str, Any], side_key: str) -> list[str]:
        """Extract country tags from a war's attackers/defenders list."""
        side = war_block.get(side_key, [])
        if isinstance(side, dict):
            side = [side]
        tags: list[str] = []
        for entry in side:
            if isinstance(entry, dict):
                tag = entry.get("tag", "")
                if tag:
                    tags.append(str(tag))
            elif isinstance(entry, str):
                tags.append(entry)
        return tags

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

        return DiplomacyState(
            truces=truce_raw,
            alliances=alliances,
            ae_map={},
        )

    def _extract_colonial(self, tree: dict[str, Any], country: str) -> ColonialState:
        c = self._country_block(tree, country)
        colonists = c.get("colonists", 0)
        if isinstance(colonists, list):
            colonists = len(colonists)
        total_colonists = self._int(c.get("num_of_colonists"), default=0)
        # Active colonies from provinces section
        active: list[dict[str, Any]] = []
        provinces = tree.get("provinces", {})
        if isinstance(provinces, dict):
            for prov_id, prov in provinces.items():
                if not isinstance(prov, dict):
                    continue
                if prov.get("owner") != country:
                    continue
                col_size = prov.get("colonysize")
                if col_size is not None:
                    active.append({
                        "province_id": prov_id,
                        "name": str(prov.get("name", "")),
                        "progress": self._int(col_size, default=0),
                    })
        return ColonialState(
            colonists_free=self._int(colonists, default=0),
            total_colonists=total_colonists,
            active_colonies=active,
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

    def _extract_trade_nodes(self, tree: dict[str, Any], country: str) -> list[TradeNodeState]:
        """Extract trade nodes where the player has merchants deployed."""
        trade_section = tree.get("trade", {})
        if not isinstance(trade_section, dict):
            return []
        nodes_raw = trade_section.get("node", [])
        if isinstance(nodes_raw, dict):
            nodes_raw = [nodes_raw]
        result: list[TradeNodeState] = []
        for node in nodes_raw:
            if not isinstance(node, dict):
                continue
            # Check if country has a merchant here
            merchants_raw = node.get("merchant", [])
            if isinstance(merchants_raw, dict):
                merchants_raw = [merchants_raw]
            has_merchant = False
            for m in merchants_raw:
                if isinstance(m, dict) and m.get("country") == country:
                    has_merchant = True
                    break
            if not has_merchant:
                continue
            result.append(TradeNodeState(
                id=self._str(node.get("definitions"), default=""),
                our_power=self._float(node.get("current"), default=0.0),
                total_value=self._float(node.get("local_value"), default=0.0),
                merchants=1,
            ))
        return result

    def _extract_provinces(self, tree: dict[str, Any], country: str) -> list[ProvinceState]:
        """Extract provinces owned by the player."""
        provinces_raw = tree.get("provinces", {})
        if not isinstance(provinces_raw, dict):
            return []
        result: list[ProvinceState] = []
        for prov_id_str, prov in provinces_raw.items():
            if not isinstance(prov, dict):
                continue
            if prov.get("owner") != country:
                continue
            col_size = prov.get("colonysize")
            result.append(ProvinceState(
                province_id=self._int(prov_id_str, default=0),
                name=self._str(prov.get("name"), default=""),
                owner=country,
                development=self._float(prov.get("base_tax", 0)) + self._float(prov.get("base_production", 0)) + self._float(prov.get("base_manpower", 0)),
                base_tax=self._float(prov.get("base_tax"), default=0.0),
                unrest=self._float(prov.get("unrest"), default=0.0),
                trade_good=self._str(prov.get("trade_goods"), default=""),
                is_colony=col_size is not None,
                colony_progress=self._int(col_size, default=0) if col_size is not None else 0,
            ))
        return result

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
