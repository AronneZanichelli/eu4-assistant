"""Risk evaluation and contextual recommendation engine.

Analyses a :class:`~eu4_assistant_bot.models.GameSnapshot` to produce
:class:`RiskAlerts` and a prioritised list of :class:`Recommendation` items.
Thresholds are configurable via :class:`~eu4_assistant_bot.config.DecisionThresholds`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .colonial import ColonialAdvisor
from .config import DecisionThresholds
from .economy import EconomyAdvisor
from .military import MilitaryAdvisor
from .models import ActionPlan, GameSnapshot

# Recommendation priority constants — tune these to adjust advisor behaviour
_PRIO_PEACE_GATE = 0.97
_PRIO_COALITION = 0.95
_PRIO_DEBT = 0.92
_PRIO_MANPOWER = 0.90
_PRIO_REBELS = 0.86
_PRIO_ARMY_ALERT = 0.82
_PRIO_BALANCE = 0.80
_PRIO_EXPANSION = 0.78
_PRIO_RECRUIT = 0.75
_PRIO_COLONIZE = 0.70
_PRIO_TRADE = 0.72
_PRIO_TECH = 0.68
_PRIO_MERCHANT = 0.66
_PRIO_TECH_ALERT = 0.64


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
    """Decision engine with explainable recommendations, core alerts, and military advisor."""

    def __init__(
        self,
        thresholds: DecisionThresholds | None = None,
        military_advisor: MilitaryAdvisor | None = None,
        colonial_advisor: ColonialAdvisor | None = None,
        economy_advisor: EconomyAdvisor | None = None,
    ):
        self.thresholds = thresholds or DecisionThresholds()
        self.military = military_advisor or MilitaryAdvisor()
        self.colonial = colonial_advisor or ColonialAdvisor()
        self.economy = economy_advisor or EconomyAdvisor()

    def evaluate_risks(self, snapshot: GameSnapshot) -> RiskAlerts:
        monthly_balance = snapshot.economy.income - snapshot.economy.expenses
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

        # ── M6: Military recommendations ────────────────────────────────────
        recommendations.extend(self._military_recommendations(snapshot))

        # ── M7: Colonial + Economy recommendations ────────────────────────
        recommendations.extend(self._colonial_recommendations(snapshot))
        recommendations.extend(self._economy_recommendations(snapshot))

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

    def _military_recommendations(self, snapshot: GameSnapshot) -> list[Recommendation]:
        """Generate military-specific recommendations (M6)."""
        recs: list[Recommendation] = []
        mil = snapshot.military

        if mil.at_war:
            # Wartime: peace gate + army alerts
            for war in mil.wars:
                if war.our_side == "attacker" and war.war_score >= 50.0:
                    recs.append(Recommendation(
                        title="Valuta trattativa di pace",
                        rationale=f"War score {war.war_score:.0f}% in '{war.war_name}': considera una pace vantaggiosa.",
                        priority=_PRIO_PEACE_GATE,
                        category="military",
                    ))
                elif war.our_side == "defender" and war.war_score <= -50.0:
                    recs.append(Recommendation(
                        title="Valuta trattativa di pace",
                        rationale=f"War score {war.war_score:.0f}% in '{war.war_name}': situazione critica, valuta pace.",
                        priority=_PRIO_PEACE_GATE,
                        category="military",
                    ))
        else:
            # Peacetime: army composition alerts
            alerts = self.military.assess_armies(snapshot)
            critical_alerts = [a for a in alerts if a.severity == "critical"]
            if critical_alerts:
                first = critical_alerts[0]
                recs.append(Recommendation(
                    title=f"Esercito '{first.army_name}' in difficoltà",
                    rationale=first.message,
                    priority=_PRIO_ARMY_ALERT,
                    category="military",
                ))

        # Recruitment recommendation (peace or war)
        plan = self.military.recommend_recruitment(snapshot)
        if plan is not None:
            recs.append(Recommendation(
                title="Recluta reggimenti",
                rationale=plan.reason,
                priority=_PRIO_RECRUIT,
                category="military",
            ))

        return recs

    def _colonial_recommendations(self, snapshot: GameSnapshot) -> list[Recommendation]:
        """Generate colonial recommendations (M7)."""
        recs: list[Recommendation] = []
        plan = self.colonial.recommend_colonization(snapshot)
        if plan is not None and plan.colonists_available > 0:
            recs.append(Recommendation(
                title="Invia colono",
                rationale=plan.reason,
                priority=_PRIO_COLONIZE,
                category="colonial",
            ))
        return recs

    def _economy_recommendations(self, snapshot: GameSnapshot) -> list[Recommendation]:
        """Generate economy recommendations (M7)."""
        recs: list[Recommendation] = []

        # Balance alert (preventive)
        balance_alert = self.economy.check_balance(snapshot)
        if balance_alert is not None:
            recs.append(Recommendation(
                title="Bilancio in calo",
                rationale=balance_alert.message,
                priority=_PRIO_BALANCE,
                category="economy",
            ))

        # Merchant steering
        advice = self.economy.recommend_merchant_steering(snapshot)
        if advice:
            top = advice[0]
            recs.append(Recommendation(
                title=f"Mercante: {top.action} a {top.node_id}",
                rationale=top.reason,
                priority=_PRIO_MERCHANT,
                category="economy",
            ))

        # Tech alerts
        tech_alerts = self.economy.check_tech_readiness(snapshot)
        if tech_alerts:
            first = tech_alerts[0]
            recs.append(Recommendation(
                title=f"Tech {first.tech_type.upper()} non pronta",
                rationale=first.message,
                priority=_PRIO_TECH_ALERT,
                category="technology",
            ))

        return recs

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
            title_lower = recommendation.title.lower()
            if "pace" in title_lower:
                return (
                    "military_peace_gate",
                    {
                        "target_metric": "war_score",
                        "current_value": "pending_confirmation",
                    },
                )
            if "recluta" in title_lower:
                total_reg = sum(
                    sum(a.composition.values()) for a in snapshot.military.armies
                )
                return (
                    "military_recruit",
                    {
                        "target_metric": "regiments",
                        "current_value": total_reg,
                        "target_above": float(snapshot.military.force_limit),
                    },
                )
            # Default: manpower recovery or army alert
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

        if recommendation.category == "colonial":
            return (
                "colonial_send_colonist",
                {
                    "target_metric": "colonists_free",
                    "current_value": snapshot.colonial.colonists_free,
                },
            )

        if recommendation.category == "technology":
            return (
                "economy_tech_preparation",
                {
                    "target_metric": "monarch_points",
                    "current_value": "accumulate",
                },
            )

        return (
            "strategy_controlled_expansion",
            {
                "target_metric": "overall_risk",
                "current_value": "stable",
            },
        )
