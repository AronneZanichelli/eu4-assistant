from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .config import DecisionThresholds
from .models import ActionPlan, GameSnapshot


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
    reasons: list["RiskReason"]


class RiskCode(str, Enum):
    COALITION_HIGH = "coalition.high"
    DEBT_OVER_RATIO = "debt.over_ratio"
    DEBT_NEGATIVE_BALANCE = "debt.negative_balance"
    MANPOWER_LOW = "manpower.low"
    REBELS_HIGH = "rebels.high"


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

    def evaluate_risks(self, snapshot: GameSnapshot) -> RiskAlerts:
        monthly_balance = snapshot.economy.income - snapshot.economy.expenses
        debt_ratio = snapshot.economy.debt / max(snapshot.economy.income, 1)
        manpower_ratio = snapshot.military.manpower / max(snapshot.military.force_limit * 1000, 1)

        coalition_risk = snapshot.risk.coalition >= self.thresholds.coalition_risk_threshold
        debt_risk = debt_ratio >= self.thresholds.debt_to_income_threshold or (
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

        if debt_ratio >= self.thresholds.debt_to_income_threshold:
            reasons.append(
                RiskReason(
                    code=RiskCode.DEBT_OVER_RATIO,
                    severity="high",
                    message="Rapporto debito/reddito oltre soglia.",
                    current_value=debt_ratio,
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

        return RiskAlerts(
            coalition_risk=coalition_risk,
            debt_risk=debt_risk,
            manpower_risk=manpower_risk,
            rebels_risk=rebels_risk,
            reasons=reasons,
        )

    def recommend(self, snapshot: GameSnapshot) -> list[Recommendation]:
        risks = self.evaluate_risks(snapshot)
        recommendations: list[Recommendation] = []

        if risks.coalition_risk:
            recommendations.append(
                Recommendation(
                    title="Riduci rischio coalizione",
                    rationale="AE/coalition risk alto: privilegia miglioramento relazioni, tregue e guerra limitata.",
                    priority=0.95,
                    category="diplomacy",
                )
            )

        if risks.debt_risk:
            recommendations.append(
                Recommendation(
                    title="Stabilizza economia",
                    rationale="Debito elevato o bilancio mensile negativo: riduci maintenance, evita nuove guerre costose.",
                    priority=0.92,
                    category="economy",
                )
            )

        if risks.manpower_risk:
            recommendations.append(
                Recommendation(
                    title="Recupera manpower",
                    rationale="Manpower critico: evita battaglie sfavorevoli, usa mercenari in fronti secondari.",
                    priority=0.90,
                    category="military",
                )
            )

        if risks.rebels_risk:
            recommendations.append(
                Recommendation(
                    title="Abbassa unrest e rischio ribelli",
                    rationale="Rivolte probabili: alza autonomy selettiva, valuta harsh treatment e presidia province instabili.",
                    priority=0.86,
                    category="internal",
                )
            )

        if not recommendations:
            recommendations.extend(
                [
                    Recommendation(
                        title="Espansione controllata",
                        rationale="Rischi principali bassi: puoi pianificare una guerra breve su target a basso attrito.",
                        priority=0.78,
                        category="strategy",
                    ),
                    Recommendation(
                        title="Ottimizza trade",
                        rationale="Bilancio stabile: reindirizza mercanti e investi su nodi ad alta resa.",
                        priority=0.72,
                        category="economy",
                    ),
                    Recommendation(
                        title="Prepara prossimo tech spike",
                        rationale="Consolidamento consigliato: conserva monarch points e allinea idea group con obiettivi campagna.",
                        priority=0.68,
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
            monthly_balance = snapshot.economy.income - snapshot.economy.expenses
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
