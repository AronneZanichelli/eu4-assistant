from __future__ import annotations

from dataclasses import dataclass, field

from .config import BotMode, SafetyLimits
from .execution.input_backend import InputBackend, StubBackend
from .execution.supervisor import ExecutionSupervisor, SupervisorConfig
from .models import ActionPlan, GameSnapshot

# Ensure all handlers are registered on import
import eu4_assistant_bot.execution.handlers  # noqa: F401


@dataclass(slots=True)
class ExecutionResult:
    plan_id: str
    action_type: str
    status: str
    reason: str
    confidence: float
    simulated_effects: dict[str, float | str] = field(default_factory=dict)


class ActionExecutor:
    """Action executor with both simulated and real execution modes.

    - simulate(): returns fake results (M2 legacy, used by tests)
    - execute(): real execution via InputBackend + ExecutionSupervisor (M8)
    """

    def __init__(
        self,
        backend: InputBackend | None = None,
        safety: SafetyLimits | None = None,
        supervisor_config: SupervisorConfig | None = None,
    ) -> None:
        self._backend = backend or StubBackend()
        self._supervisor = ExecutionSupervisor(
            backend=self._backend,
            safety=safety or SafetyLimits(),
            config=supervisor_config,
        )

    @property
    def supervisor(self) -> ExecutionSupervisor:
        return self._supervisor

    def execute(self, plan: ActionPlan, snapshot: GameSnapshot, mode: BotMode) -> ExecutionResult:
        """Real execution via supervisor + registered handlers."""
        result = self._supervisor.execute_plan(plan, snapshot, mode)
        if result.success:
            status = "executed"
        elif result.pre_check.message == "awaiting_confirmation":
            status = "awaiting_confirmation"
        else:
            status = "failed"
        return ExecutionResult(
            plan_id=plan.id,
            action_type=plan.action_type,
            status=status,
            reason=result.message,
            confidence=plan.confidence,
        )

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
