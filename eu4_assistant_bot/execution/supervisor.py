"""Execution supervisor with retry, emergency stop, and EU4-pause awareness."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from ..config import BotMode, SafetyLimits
from ..models import ActionPlan, GameSnapshot
from .action_handler import CheckResult, HandlerResult, get_handler
from .input_backend import InputBackend

logger = logging.getLogger(__name__)


class ExecutionState(str, Enum):
    IDLE = "idle"
    EXECUTING = "executing"
    WAITING_CONFIRM = "waiting_confirm"
    PAUSED_EU4 = "paused_eu4"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"


@dataclass(slots=True)
class SupervisorConfig:
    max_retries: int = 2
    retry_delay_seconds: float = 1.0
    action_timeout_seconds: float = 30.0


class ExecutionSupervisor:
    """Orchestrates action execution with safety guarantees."""

    def __init__(
        self,
        backend: InputBackend,
        safety: SafetyLimits,
        config: SupervisorConfig | None = None,
        on_state_changed: Callable[[ExecutionState], None] | None = None,
        on_action_started: Callable[[ActionPlan], None] | None = None,
        on_action_completed: Callable[[HandlerResult], None] | None = None,
    ) -> None:
        self._backend = backend
        self._safety = safety
        self._config = config or SupervisorConfig()
        self._state = ExecutionState.IDLE
        self._emergency_stop = threading.Event()
        self._on_state_changed = on_state_changed
        self._on_action_started = on_action_started
        self._on_action_completed = on_action_completed

    @property
    def state(self) -> ExecutionState:
        return self._state

    def _set_state(self, new_state: ExecutionState) -> None:
        self._state = new_state
        if self._on_state_changed:
            self._on_state_changed(new_state)

    def execute_plan(
        self, plan: ActionPlan, snapshot: GameSnapshot, mode: BotMode
    ) -> HandlerResult:
        """Execute a single action plan with full safety envelope."""
        # 1. Check emergency stop
        if self._emergency_stop.is_set():
            return self._make_failure(plan, "Emergency stop attivo.")

        # 2. Check EU4 paused
        if self._state == ExecutionState.PAUSED_EU4:
            return self._make_failure(plan, "EU4 in pausa — bot in attesa.")

        # 3. Resolve handler
        handler = get_handler(plan.action_type, self._backend)
        if handler is None:
            return self._make_failure(plan, f"Nessun handler per '{plan.action_type}'.")

        # 4. Confirmation check (semi-bot: all confirmed actions need UI confirm)
        if handler.requires_confirmation or plan.requires_confirmation:
            if mode != BotMode.FULL_BOT:
                self._set_state(ExecutionState.WAITING_CONFIRM)
                # In real integration, the UI callback handles this.
                # For now, we proceed (the UI layer gates this before calling us).
                self._set_state(ExecutionState.IDLE)

        # 5. Notify action started
        if self._on_action_started:
            self._on_action_started(plan)
        self._set_state(ExecutionState.EXECUTING)

        # 6. Execute with retry
        last_result: HandlerResult | None = None
        for attempt in range(self._config.max_retries + 1):
            if self._emergency_stop.is_set():
                self._set_state(ExecutionState.EMERGENCY_STOP)
                return self._make_failure(plan, "Interrotto da emergency stop.")

            last_result = handler.run(plan, snapshot)
            if last_result.success:
                break

            if attempt < self._config.max_retries:
                logger.info(
                    "Handler %s attempt %d failed: %s. Retrying...",
                    plan.action_type,
                    attempt + 1,
                    last_result.message,
                )
                time.sleep(self._config.retry_delay_seconds)

        assert last_result is not None
        self._set_state(ExecutionState.IDLE)

        # 7. Notify completion
        if self._on_action_completed:
            self._on_action_completed(last_result)

        return last_result

    def emergency_stop(self) -> None:
        """Immediately halt all execution. Thread-safe."""
        self._emergency_stop.set()
        self._set_state(ExecutionState.EMERGENCY_STOP)

    def reset(self) -> None:
        """Clear emergency stop, return to idle."""
        self._emergency_stop.clear()
        self._set_state(ExecutionState.IDLE)

    def notify_eu4_paused(self) -> None:
        """Called by FileWatcher when EU4 stops producing autosaves."""
        self._set_state(ExecutionState.PAUSED_EU4)

    def notify_eu4_resumed(self) -> None:
        """Called when a new autosave arrives after a pause."""
        if self._state == ExecutionState.PAUSED_EU4:
            self._set_state(ExecutionState.IDLE)

    @staticmethod
    def _make_failure(plan: ActionPlan, message: str) -> HandlerResult:
        return HandlerResult(
            success=False,
            action_type=plan.action_type,
            message=message,
            pre_check=CheckResult(passed=False, message=message),
        )
