from __future__ import annotations

from dataclasses import dataclass, field

from .config import BotMode
from .models import ActionPlan


@dataclass(slots=True)
class ExecutionResult:
    plan_id: str
    action_type: str
    status: str
    reason: str
    confidence: float
    simulated_effects: dict[str, float | str] = field(default_factory=dict)


class ActionExecutor:
    """Simulated executor for action plans (pre-local integration stage)."""

    def simulate(self, plans: list[ActionPlan], mode: BotMode) -> list[ExecutionResult]:
        results: list[ExecutionResult] = []

        for plan in plans:
            if mode == BotMode.ASSIST and plan.requires_confirmation:
                results.append(
                    ExecutionResult(
                        plan_id=plan.id,
                        action_type=plan.action_type,
                        status="skipped",
                        reason="confirmation_required_in_assist_mode",
                        confidence=plan.confidence,
                    )
                )
                continue

            results.append(
                ExecutionResult(
                    plan_id=plan.id,
                    action_type=plan.action_type,
                    status="simulated_executed",
                    reason="simulated_pipeline",
                    confidence=plan.confidence,
                    simulated_effects=self._simulate_effects(plan),
                )
            )

        return results

    @staticmethod
    def _simulate_effects(plan: ActionPlan) -> dict[str, float | str]:
        target_metric = str(plan.expected_outcome.get("target_metric", "unknown"))

        if "target_below" in plan.expected_outcome:
            target = float(plan.expected_outcome["target_below"])
            return {
                "target_metric": target_metric,
                "projected_direction": "down",
                "projected_value": round(target * 0.95, 4),
            }

        if "target_above" in plan.expected_outcome:
            target = float(plan.expected_outcome["target_above"])
            return {
                "target_metric": target_metric,
                "projected_direction": "up",
                "projected_value": round(target * 1.05, 4),
            }

        return {
            "target_metric": target_metric,
            "projected_direction": "stable",
            "projected_value": "n/a",
        }
