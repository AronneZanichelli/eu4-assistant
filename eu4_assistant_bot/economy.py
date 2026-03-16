from __future__ import annotations

from dataclasses import dataclass

from .models import GameSnapshot, TradeNodeState

# Default tech costs per level (EU4 base, simplified)
_BASE_TECH_COST = 600

# Balance alert threshold (ducats/month)
_DEFAULT_BALANCE_THRESHOLD = 1.0


# ── Support dataclasses ──────────────────────────────────────────────────────

@dataclass(slots=True)
class MerchantAdvice:
    node_id: str
    action: str              # "steer" | "collect"
    reason: str
    expected_value: float    # node total value


@dataclass(slots=True)
class TechAlert:
    tech_type: str           # "adm" | "dip" | "mil"
    points_needed: int
    points_available: int
    message: str


@dataclass(slots=True)
class BalanceAlert:
    current_balance: float
    threshold: float
    message: str


class EconomyAdvisor:
    """M7 economy logic: merchant steering, tech alerts, balance monitoring."""

    def __init__(self, balance_threshold: float = _DEFAULT_BALANCE_THRESHOLD):
        self.balance_threshold = balance_threshold

    def recommend_merchant_steering(self, snapshot: GameSnapshot) -> list[MerchantAdvice]:
        """Suggest merchant actions based on trade node values.

        Strategy: steer trade in lower-value nodes, collect in the highest-value node.
        """
        nodes = snapshot.trade_nodes
        if not nodes:
            return []

        # Sort by total value descending
        sorted_nodes = sorted(nodes, key=lambda n: n.total_value, reverse=True)

        advice: list[MerchantAdvice] = []
        for i, node in enumerate(sorted_nodes):
            if i == 0:
                # Highest value node → collect
                advice.append(MerchantAdvice(
                    node_id=node.id,
                    action="collect",
                    reason=f"Nodo a maggior valore ({node.total_value:.1f}): raccogli qui.",
                    expected_value=node.total_value,
                ))
            else:
                # Other nodes → steer toward home node
                advice.append(MerchantAdvice(
                    node_id=node.id,
                    action="steer",
                    reason=f"Nodo secondario ({node.total_value:.1f}): reindirizza verso nodo principale.",
                    expected_value=node.total_value,
                ))

        return advice

    def check_tech_readiness(self, snapshot: GameSnapshot) -> list[TechAlert]:
        """Alert when monarch points are insufficient for next tech level."""
        tech = snapshot.tech
        alerts: list[TechAlert] = []

        checks = [
            ("adm", tech.adm_tech, tech.adm_points),
            ("dip", tech.dip_tech, tech.dip_points),
            ("mil", tech.mil_tech, tech.mil_points),
        ]

        for tech_type, level, points in checks:
            cost = self._estimate_tech_cost(level)
            if points < cost:
                alerts.append(TechAlert(
                    tech_type=tech_type,
                    points_needed=cost,
                    points_available=points,
                    message=f"Tech {tech_type.upper()} lv{level + 1}: servono {cost} punti, ne hai {points}.",
                ))

        return alerts

    def check_balance(self, snapshot: GameSnapshot) -> BalanceAlert | None:
        """Alert when monthly balance drops below threshold (preventive)."""
        balance = snapshot.economy.income - snapshot.economy.expenses
        if balance < self.balance_threshold:
            return BalanceAlert(
                current_balance=round(balance, 2),
                threshold=self.balance_threshold,
                message=f"Bilancio mensile basso ({balance:+.1f} ducati). Riduci spese o aumenta entrate.",
            )
        return None

    @staticmethod
    def _estimate_tech_cost(current_level: int) -> int:
        """Rough tech cost estimate. EU4 cost scales with level."""
        # Simplified: base cost increases ~50 per level above 3
        if current_level <= 3:
            return _BASE_TECH_COST
        return _BASE_TECH_COST + (current_level - 3) * 50
