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
    WarState,
)

logger = logging.getLogger(__name__)


class StateExtractor:

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
        total_merchants = self._int(c.get("num_of_merchants"), default=0)
        return EconomyState(
            treasury=self._float(c.get("treasury"), default=0.0),
            income=self._float(c.get("income"), default=0.0),
            expenses=self._float(c.get("expenses"), default=0.0),
            debt=self._float(c.get("loan_size"), default=0.0),
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
                id=self._str(a.get(
