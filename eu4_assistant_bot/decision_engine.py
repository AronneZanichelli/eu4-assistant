"""Risk evaluation and contextual recommendation engine.

Analyses a :class:`~eu4_assistant_bot.models.GameSnapshot` to produce
:class:`RiskAlerts` and a prioritised list of :class:`Recommendation` items.
Thresholds are configurable via :class:`~eu4_assistant_bot.config.DecisionThresholds`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .config import DecisionThresholds
from .models import ActionPlan, GameSnapshot

# Recommendation priority constants — tune these to adjust advisor behaviour
_PRIO_COALITION          = 0.95
_PRIO_DEBT               = 0.92
_PRIO_MANPOWER           = 0.90
_PRIO_REBELS             = 0.86
_PRIO_WARTIME_REINFORCE  = 0.93   # M6: wartime + critical manpower
_PRIO_ARMY_HEALTH        = 0.82   # M6: peacetime army below force limit
_PRIO_EXPANSION          = 0.78
_PRIO_ARMY_FRAGMENTED    = 0.70   # M6: many small armies
_PRIO_TRADE              = 0.72
_PRIO_TECH               = 0.68


@dataclass(slots=True)
class Recommendation:
    title: str
    rationale: str
    priority: float
    category: str


@dataclass(slots=True)
class RiskAlerts:
    coalition_risk: bool
    debt_risk: bool
    manpower_risk: bool
    rebels_risk: bool
    army_risk: bool
    reasons: list["RiskReason"]


class RiskCode(str, Enum):
    COALITION_HIGH         = "coalition.high"
    DEBT_OVER_RATIO        = "debt.over_ratio"
    DEBT_NEGATIVE_BALANCE  = "debt.negative_balance"
    MANPOWER_LOW           = "manpower.low"
    REBELS_HIGH            = "rebels.high"
    # M6 military
    ARMY_BELOW_FORCE_LIMIT = "army.below_force_limit"
    ARMY_FRAGMENTED        = "army.fragmented"
    WARTIME_MANPOWER_LOW   = "wartime.manpower_low"


@dataclass(slots=True)
class RiskReason:
    code: RiskCode
    severity: str
    message: str
    current_value: float
    threshold_value: float


class DecisionEngine:
    """M2 decision engine with explainable recommendations and core alerts."""

    def __init__(self, thresholds: DecisionThresholds | None = None):
        self.thresholds = thresholds or DecisionThresholds()

    @staticmethod
    def _monthly_balance(snapshot: GameSnapshot) -> float:
        return snapshot.economy.income - snapshot.economy.expenses

    def evaluate_risks(self, snapshot: GameSnapshot) -> RiskAlerts:
        monthly_balance = self._monthly_balance(snapshot)
        # debt_ratio_pct: expressed as percentage (e.g. 24.0 = 24%)
        # income == 0 is treated as infinite debt ratio (capped at 9999)
        income = max(snapshot.economy.income, 0.01)
        debt_ratio_pct = min((snapshot.economy.debt / income) * 100.0, 9999.0)
        manpower_ratio = snapshot.military.manpower / max(snapshot.military.force_limit * 1000, 1)

        coalition_risk = snapshot.risk.coalition >= self.thresholds.coalition_risk_threshold
        debt_risk = debt_ratio_pct >= self.thresholds.debt_to_income_threshold or (
            snapshot.economy.debt > 0 and monthly_balance < 0
        )
        manpower_risk = manpower_ratio <= self.thresholds.manpower_ratio_threshold
        rebels_risk = snapshot.risk.rebels >= self.thresholds.rebels_risk_threshold

        reasons: list[RiskReason] = []
        if coalition_risk:
            reasons.append(
                RiskReason(
                    code=RiskCode.COALITION_HIGH,
                    severity="high",
                    message="Coalition risk sopra soglia configurata.",
                    current_value=snapshot.risk.coalition,
                    threshold_value=self.thresholds.coalition_risk_threshold,
                )
            )

        if debt_ratio_pct >= self.thresholds.debt_to_income_threshold:
            reasons.append(
                RiskReason(
                    code=RiskCode.DEBT_OVER_RATIO,
                    severity="high",
                    message="Rapporto debito/reddito oltre soglia.",
                    current_value=debt_ratio_pct,
                    threshold_value=self.thresholds.debt_to_income_threshold,
                )
            )

        if snapshot.economy.debt > 0 and monthly_balance < 0:
            reasons.append(
                RiskReason(
                    code=RiskCode.DEBT_NEGATIVE_BALANCE,
                    severity="medium",
                    message="Debito presente con bilancio mensile negativo.",
                    current_value=monthly_balance,
                    threshold_value=0.0,
                )
            )

        if manpower_risk:
            reasons.append(
                RiskReason(
                    code=RiskCode.MANPOWER_LOW,
                    severity="high",
                    message="Manpower ratio sotto soglia configurata.",
                    current_value=manpower_ratio,
                    threshold_value=self.thresholds.manpower_ratio_threshold,
                )
            )

        if rebels_risk:
            reasons.append(
                RiskReason(
                    code=RiskCode.REBELS_HIGH,
                    severity="medium",
                    message="Rischio rivolte elevato rispetto alla soglia.",
                    current_value=snapshot.risk.rebels,
                    threshold_value=self.thresholds.rebels_risk_threshold,
                )
            )

        military_reasons = self.evaluate_military(snapshot)
        reasons.extend(military_reasons)
        army_risk = len(military_reasons) > 0

        return RiskAlerts(
            coalition_risk=coalition_risk,
            debt_risk=debt_risk,
            manpower_risk=manpower_risk,
            rebels_risk=rebels_risk,
            army_risk=army_risk,
            reasons=reasons,
        )

    def evaluate_military(self, snapshot: GameSnapshot) -> list[RiskReason]:
        """M6: Evaluate military situation and return military-specific risk reasons."""
        reasons: list[RiskReason] = []
        at_war = snapshot.diplomacy.active_wars > 0
        total_strength = sum(a.strength for a in snapshot.military.armies)
        force_limit_k = snapshot.military.force_limit * 1000

        # Peacetime: armies well below force limit → recruit more
        if not at_war and force_limit_k > 0:
            ratio = total_strength / force_limit_k
            if ratio < self.thresholds.army_strength_threshold:
                reasons.append(
                    RiskReason(
                        code=RiskCode.ARMY_BELOW_FORCE_LIMIT,
                        severity="medium",
                        message=f"Truppe al {ratio:.0%} del force limit — valuta reclutamento.",
                        current_value=ratio,
                        threshold_value=self.thresholds.army_strength_threshold,
                    )
                )

        # Army fragmentation: many small stacks are vulnerable to stack wipes
        small_armies = [a for a in snapshot.military.armies if a.strength < 5000]
        if len(small_armies) > 3:
            reasons.append(
                RiskReason(
                    code=RiskCode.ARMY_FRAGMENTED,
                    severity="low",
                    message=f"{len(small_armies)} armate sotto 5k — rischio stack wipe in battaglia.",
                    current_value=float(len(small_armies)),
                    threshold_value=3.0,
                )
            )

        # Wartime: low manpower during active war is critical
        if at_war and snapshot.military.manpower < self.thresholds.wartime_manpower_min:
            reasons.append(
                RiskReason(
                    code=RiskCode.WARTIME_MANPOWER_LOW,
                    severity="high",
                    message="Manpower critico in guerra — evita battaglie offensive, usa mercenari.",
                    current_value=float(snapshot.military.manpower),
                    threshold_value=float(self.thresholds.wartime_manpower_min),
                )
            )

        return reasons

    def recommend(self, snapshot: GameSnapshot) -> list[Recommendation]:
        risks = self.evaluate_risks(snapshot)
        recommendations: list[Recommendation] = []

        if risks.coalition_risk:
            recommendations.append(
                Recommendation(
                    title="Riduci rischio coalizione",
                    rationale="AE/coalition risk alto: privilegia miglioramento relazioni, tregue e guerra limitata.",
                    priority=_PRIO_COALITION,
                    category="diplomacy",
                )
            )

        if risks.debt_risk:
            recommendations.append(
                Recommendation(
                    title="Stabilizza economia",
                    rationale="Debito elevato o bilancio mensile negativo: riduci maintenance, evita nuove guerre costose.",
                    priority=_PRIO_DEBT,
                    category="economy",
                )
            )

        if risks.manpower_risk:
            recommendations.append(
                Recommendation(
                    title="Recupera manpower",
                    rationale="Manpower critico: evita battaglie sfavorevoli, usa mercenari in fronti secondari.",
                    priority=_PRIO_MANPOWER,
                    category="military",
                )
            )

        if risks.rebels_risk:
            recommendations.append(
                Recommendation(
                    title="Abbassa unrest e rischio ribelli",
                    rationale="Rivolte probabili: alza autonomy selettiva, valuta harsh treatment e presidia province instabili.",
                    priority=_PRIO_REBELS,
                    category="internal",
                )
            )

        # M6 military recommendations
        at_war = snapshot.diplomacy.active_wars > 0
        for reason in risks.reasons:
            if reason.code == RiskCode.WARTIME_MANPOWER_LOW:
                recommendations.append(
                    Recommendation(
                        title="Rinforza le armate in guerra",
                        rationale="Manpower critico durante una guerra attiva: usa mercenari sui fronti secondari, evita battaglie offensive fino al recupero.",
                        priority=_PRIO_WARTIME_REINFORCE,
                        category="military",
                    )
                )
                break
            if reason.code == RiskCode.ARMY_BELOW_FORCE_LIMIT and not at_war:
                recommendations.append(
                    Recommendation(
                        title="Recluta fino al force limit",
                        rationale="Le truppe sono sotto il 50% del force limit: recluta fanteria per consolidare la forza militare.",
                        priority=_PRIO_ARMY_HEALTH,
                        category="military",
                    )
                )
                break
            if reason.code == RiskCode.ARMY_FRAGMENTED:
                recommendations.append(
                    Recommendation(
                        title="Consolida le armate frammentate",
                        rationale="Molte armate piccole sono vulnerabili a stack wipe: unisci le unità in stack da almeno 10k.",
                        priority=_PRIO_ARMY_FRAGMENTED,
                        category="military",
                    )
                )
                break

        if not recommendations:
            recommendations.extend(
                [
                    Recommendation(
                        title="Espansione controllata",
                        rationale="Rischi principali bassi: puoi pianificare una guerra breve su target a basso attrito.",
                        priority=_PRIO_EXPANSION,
                        category="strategy",
                    ),
                    Recommendation(
                        title="Ottimizza trade",
                        rationale="Bilancio stabile: reindirizza mercanti e investi su nodi ad alta resa.",
                        priority=_PRIO_TRADE,
                        category="economy",
                    ),
                    Recommendation(
                        title="Prepara prossimo tech spike",
                        rationale="Consolidamento consigliato: conserva monarch points e allinea idea group con obiettivi campagna.",
                        priority=_PRIO_TECH,
                        category="technology",
                    ),
                ]
            )

        ordered = sorted(recommendations, key=lambda item: item.priority, reverse=True)
        return ordered[:3]

    def build_action_plans(self, snapshot: GameSnapshot) -> list[ActionPlan]:
        recommendations = self.recommend(snapshot)
        plans: list[ActionPlan] = []

        for rec in recommendations:
            action_type, expected_outcome = self._map_recommendation_to_action(rec, snapshot)
            plans.append(
                ActionPlan(
                    id=f"{action_type}:{int(rec.priority * 100)}",
                    action_type=action_type,
                    priority=rec.priority,
                    confidence=min(0.95, max(0.55, rec.priority - 0.05)),
                    expected_outcome=expected_outcome,
                    requires_confirmation=True,
                )
            )

        return plans

    def _map_recommendation_to_action(
        self, recommendation: Recommendation, snapshot: GameSnapshot
    ) -> tuple[str, dict[str, float | str]]:
        if recommendation.category == "diplomacy":
            return (
                "diplomacy_reduce_coalition",
                {
                    "target_metric": "coalition_risk",
                    "current_value": snapshot.risk.coalition,
                    "target_below": self.thresholds.coalition_risk_threshold,
                },
            )

        if recommendation.category == "economy":
            monthly_balance = self._monthly_balance(snapshot)
            return (
                "economy_stabilize_budget",
                {
                    "target_metric": "monthly_balance",
                    "current_value": monthly_balance,
                    "target_above": 0.0,
                },
            )

        if recommendation.category == "military":
            manpower_ratio = snapshot.military.manpower / max(snapshot.military.force_limit * 1000, 1)
            return (
                "military_recover_manpower",
                {
                    "target_metric": "manpower_ratio",
                    "current_value": manpower_ratio,
                    "target_above": self.thresholds.manpower_ratio_threshold,
                },
            )

        if recommendation.category == "internal":
            return (
                "internal_reduce_unrest",
                {
                    "target_metric": "rebels_risk",
                    "current_value": snapshot.risk.rebels,
                    "target_below": self.thresholds.rebels_risk_threshold,
                },
            )

        return (
            "strategy_controlled_expansion",
            {
                "target_metric": "overall_risk",
                "current_value": "stable",
            },
        )
