"""Action executor — simulated (M1-M7) and real (M8+).

:class:`ActionExecutor` evaluates :class:`~eu4_assistant_bot.models.ActionPlan`
items and returns :class:`ExecutionResult` objects.

* ``simulate()`` — original simulation-only path (kept for tests and ASSIST mode).
* ``execute()`` — M8 real path: pauses the game via pyautogui and logs advisory.
  Falls back gracefully if pyautogui is not installed (``pip install eu4-assistant-bot[bot]``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .config import BotMode
from .models import ActionPlan

logger = logging.getLogger(__name__)

# Human-readable descriptions for each action type (used in advisory log)
_ACTION_DESCRIPTIONS: dict[str, str] = {
    "diplomacy_reduce_coalition": "Reduce coalition risk: improve relations, sign truces, limit expansion",
    "economy_stabilize_budget": "Stabilize budget: reduce maintenance, avoid costly wars",
    "military_recover_manpower": "Recover manpower: avoid offensive battles, hire mercenaries",
    "internal_reduce_unrest": "Reduce unrest: increase autonomy selectively, harsh treatment, garrison",
    "colonial_send_colonist": "Send colonist: assign free colonist to a coastal or resource-rich province",
    "trade_deploy_merchant": "Deploy merchant: redirect to a high-value trade node",
    "strategy_controlled_expansion": "Controlled expansion: plan a short war on a low-attrition target",
    "military_recover_manpower": "Recover manpower: avoid offensive battles, use mercenaries",
}


@dataclass(slots=True)
class ExecutionResult:
    plan_id: str
    action_type: str
    status: str
    reason: str
    confidence: float
    simulated_effects: dict[str, float | str] = field(default_factory=dict)


class ActionExecutor:
    """Executor for action plans.  Supports simulation (tests) and real execution (M8)."""

    def simulate(self, plans: list[ActionPlan], mode: BotMode) -> list[ExecutionResult]:
        """Original simulation path — used for testing and ASSIST mode advisory."""
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

    def execute(self, plans: list[ActionPlan], mode: BotMode) -> list[ExecutionResult]:
        """M8 real execution path.

        Behaviour by mode:

        * ``ASSIST``   — advisory log only; no game interaction.
        * ``SEMI_BOT`` — pause game via Space + advisory log.
          Confirmation dialog is handled at the UI layer before calling this.
        * ``FULL_BOT`` — same as SEMI_BOT for M8 MVP; full menu navigation
          is deferred to M9.

        Falls back gracefully if ``pyautogui`` is not installed.
        """
        results: list[ExecutionResult] = []

        for plan in plans:
            if mode == BotMode.ASSIST:
                description = _ACTION_DESCRIPTIONS.get(plan.action_type, plan.action_type)
                logger.info("ADVISORY [%s]: %s", plan.action_type, description)
                results.append(
                    ExecutionResult(
                        plan_id=plan.id,
                        action_type=plan.action_type,
                        status="advisory",
                        reason="assist_mode_advisory_only",
                        confidence=plan.confidence,
                        simulated_effects=self._simulate_effects(plan),
                    )
                )
                continue

            # SEMI_BOT / FULL_BOT: interact with game
            description = _ACTION_DESCRIPTIONS.get(plan.action_type, plan.action_type)
            logger.info("EXECUTE [%s]: %s", plan.action_type, description)
            paused = self._pause_game()
            results.append(
                ExecutionResult(
                    plan_id=plan.id,
                    action_type=plan.action_type,
                    status="executed" if paused else "executed_no_pause",
                    reason="game_paused_via_space" if paused else "pyautogui_unavailable_advisory_only",
                    confidence=plan.confidence,
                    simulated_effects=self._simulate_effects(plan),
                )
            )

        return results

    @staticmethod
    def _pause_game() -> bool:
        """Send Space key to pause EU4.  Returns True if the key was sent.

        Requires ``pyautogui`` (``pip install eu4-assistant-bot[bot]``).
        Falls back to advisory-only if not installed.
        """
        try:
            import pyautogui  # type: ignore[import]  # noqa: PLC0415
        except ImportError:
            logger.warning(
                "pyautogui not installed — install eu4-assistant-bot[bot] to enable "
                "game interaction.  Running in advisory-only mode."
            )
            return False
        try:
            pyautogui.press("space")
            logger.debug("Space key sent to EU4 (pause toggle).")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to send Space key via pyautogui: %s", exc)
            return False

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
