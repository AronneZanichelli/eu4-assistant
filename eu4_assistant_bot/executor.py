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
from typing import Callable

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
}


@dataclass(slots=True)
class ExecutionResult:
    plan_id: str
    action_type: str
    status: str
    reason: str
    confidence: float
    simulated_effects: dict[str, float | str] = field(default_factory=dict)


def _default_key_sender(key: str) -> bool:
    """Send a key to the focused window via pyautogui, with FAILSAFE enabled.

    Returns True if the key was sent.  Falls back to advisory-only (False) when
    pyautogui is not installed (``pip install eu4-assistant-bot[bot]``).
    """
    try:
        import pyautogui  # type: ignore[import]  # noqa: PLC0415
    except ImportError:
        logger.warning(
            "pyautogui not installed — install eu4-assistant-bot[bot] to enable "
            "game interaction.  Running in advisory-only mode."
        )
        return False
    pyautogui.FAILSAFE = True  # moving the mouse to a screen corner aborts (safety)
    try:
        pyautogui.press(key)
        logger.debug("Key '%s' sent to EU4.", key)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to send key '%s' via pyautogui: %s", key, exc)
        return False


def _default_focus_check() -> bool:
    """Best-effort guard that the foreground window is EU4.

    Returns True when the active window title looks like EU4, or when focus
    cannot be determined (no window backend) — there ``FAILSAFE`` remains the
    backstop.  Returns False only when a window is identifiable and is clearly
    not EU4, so a misfire cannot type into another application.
    """
    try:
        import pyautogui  # type: ignore[import]  # noqa: PLC0415

        get_title = getattr(pyautogui, "getActiveWindowTitle", None)
        title = get_title() if callable(get_title) else None
    except Exception:  # noqa: BLE001 — any backend failure means "cannot determine"
        return True
    if not title:
        return True
    lowered = title.lower()
    return "europa universalis" in lowered or "eu4" in lowered


class ActionExecutor:
    """Executor for action plans.  Supports simulation (tests) and real execution (M8).

    ``key_sender`` and ``focus_check`` are injectable for testing (the codebase
    favours dependency injection over mocking).
    """

    def __init__(
        self,
        key_sender: Callable[[str], bool] | None = None,
        focus_check: Callable[[], bool] | None = None,
    ) -> None:
        self._key_sender = key_sender or _default_key_sender
        self._focus_check = focus_check or _default_focus_check

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

    def execute(
        self,
        plans: list[ActionPlan],
        mode: BotMode,
        confirm: Callable[[ActionPlan], bool] | None = None,
    ) -> list[ExecutionResult]:
        """M8 real execution path with the bot-safety confirmation gate (M1).

        Behaviour by mode:

        * ``ASSIST``   — advisory log only; no game interaction.
        * ``SEMI_BOT`` — every real action requires explicit confirmation
          (``confirm(plan)`` must return True) before any keystroke.
        * ``FULL_BOT`` — autonomous, except actions flagged
          ``requires_confirmation`` still need an explicit acknowledgement via
          ``confirm``.

        A plan that needs acknowledgement but does not get it is returned with
        status ``"blocked"`` and never reaches the keyboard, regardless of
        caller.  Before any keystroke the foreground window is checked and
        ``pyautogui.FAILSAFE`` is enabled.  Falls back gracefully if
        ``pyautogui`` is not installed.
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

            # Safety gate (M1): SEMI_BOT confirms every action; FULL_BOT confirms
            # only actions flagged requires_confirmation.  No confirmation => no
            # keystroke, whatever the caller is.
            needs_ack = plan.requires_confirmation or mode == BotMode.SEMI_BOT
            if needs_ack and not (confirm is not None and confirm(plan)):
                logger.warning("BLOCKED [%s]: confirmation required but not granted", plan.action_type)
                results.append(
                    ExecutionResult(
                        plan_id=plan.id,
                        action_type=plan.action_type,
                        status="blocked",
                        reason="confirmation_required",
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

    def _pause_game(self) -> bool:
        """Send Space to pause EU4 — only if EU4 is focused.  Returns True if sent.

        The focus check prevents a misfire from typing into another application;
        the keystroke itself (and ``FAILSAFE``) is handled by the key sender.
        """
        if not self._focus_check():
            logger.warning("EU4 window not focused — skipping keystroke (safety guard).")
            return False
        return self._key_sender("space")

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
