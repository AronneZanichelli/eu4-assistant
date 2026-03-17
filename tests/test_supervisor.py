"""Tests for ExecutionSupervisor."""
import time
import threading

from eu4_assistant_bot.config import BotMode, SafetyLimits
from eu4_assistant_bot.execution.action_handler import (
    ActionHandler,
    CheckResult,
    register_handler,
)
from eu4_assistant_bot.execution.input_backend import StubBackend
from eu4_assistant_bot.execution.supervisor import (
    ExecutionState,
    ExecutionSupervisor,
    SupervisorConfig,
)
from eu4_assistant_bot.models import ActionPlan, GameSnapshot


def _make_plan(action_type: str = "military_recruit", requires_confirmation: bool = False) -> ActionPlan:
    return ActionPlan(
        id="test:1",
        action_type=action_type,
        priority=0.8,
        confidence=0.7,
        requires_confirmation=requires_confirmation,
    )


def _make_snapshot(manpower: int = 5000, force_limit: int = 20) -> GameSnapshot:
    snap = GameSnapshot.empty(country="FRA")
    snap.military.manpower = manpower
    snap.military.force_limit = force_limit
    return snap


class TestSupervisorBasic:
    def test_initial_state_is_idle(self) -> None:
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits())
        assert sup.state == ExecutionState.IDLE

    def test_execute_plan_success(self) -> None:
        backend = StubBackend()
        sup = ExecutionSupervisor(backend, SafetyLimits())
        plan = _make_plan("military_recruit")
        snap = _make_snapshot(manpower=5000, force_limit=20)

        result = sup.execute_plan(plan, snap, BotMode.FULL_BOT)
        assert result.success is True
        assert sup.state == ExecutionState.IDLE

    def test_execute_plan_unknown_handler(self) -> None:
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits())
        plan = _make_plan("totally_unknown_action")

        result = sup.execute_plan(plan, GameSnapshot.empty(), BotMode.FULL_BOT)
        assert result.success is False
        assert "Nessun handler" in result.message


class TestEmergencyStop:
    def test_emergency_stop_prevents_execution(self) -> None:
        backend = StubBackend()
        sup = ExecutionSupervisor(backend, SafetyLimits())
        sup.emergency_stop()

        result = sup.execute_plan(_make_plan(), _make_snapshot(), BotMode.FULL_BOT)
        assert result.success is False
        assert "Emergency stop" in result.message
        assert len(backend.calls) == 0

    def test_reset_clears_emergency_stop(self) -> None:
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits())
        sup.emergency_stop()
        assert sup.state == ExecutionState.EMERGENCY_STOP
        sup.reset()
        assert sup.state == ExecutionState.IDLE

    def test_emergency_stop_is_thread_safe(self) -> None:
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits())
        # The emergency_stop flag is a threading.Event — it's inherently thread-safe
        sup.emergency_stop()
        assert sup._emergency_stop.is_set()
        sup.reset()
        assert not sup._emergency_stop.is_set()


class TestEu4PauseAwareness:
    def test_eu4_paused_blocks_execution(self) -> None:
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits())
        sup.notify_eu4_paused()
        assert sup.state == ExecutionState.PAUSED_EU4

        result = sup.execute_plan(_make_plan(), _make_snapshot(), BotMode.FULL_BOT)
        assert result.success is False
        assert "pausa" in result.message.lower()

    def test_eu4_resumed_restores_idle(self) -> None:
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits())
        sup.notify_eu4_paused()
        sup.notify_eu4_resumed()
        assert sup.state == ExecutionState.IDLE

    def test_eu4_resumed_only_from_paused(self) -> None:
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits())
        sup.emergency_stop()
        sup.notify_eu4_resumed()  # should NOT clear emergency stop
        assert sup.state == ExecutionState.EMERGENCY_STOP


class TestRetry:
    def test_retry_config(self) -> None:
        config = SupervisorConfig(max_retries=0, retry_delay_seconds=0.0)
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits(), config=config)

        # Pre-check fails for recruit when manpower=0 — no retry helps
        snap = _make_snapshot(manpower=0, force_limit=20)
        plan = _make_plan("military_recruit")
        result = sup.execute_plan(plan, snap, BotMode.FULL_BOT)
        assert result.success is False


class TestCallbacks:
    def test_state_changed_callback(self) -> None:
        states: list[ExecutionState] = []
        sup = ExecutionSupervisor(
            StubBackend(),
            SafetyLimits(),
            on_state_changed=lambda s: states.append(s),
        )
        sup.execute_plan(_make_plan(), _make_snapshot(), BotMode.FULL_BOT)
        assert ExecutionState.EXECUTING in states
        assert states[-1] == ExecutionState.IDLE

    def test_action_started_callback(self) -> None:
        started: list[ActionPlan] = []
        sup = ExecutionSupervisor(
            StubBackend(),
            SafetyLimits(),
            on_action_started=lambda p: started.append(p),
        )
        plan = _make_plan()
        sup.execute_plan(plan, _make_snapshot(), BotMode.FULL_BOT)
        assert len(started) == 1
        assert started[0].id == plan.id

    def test_action_completed_callback(self) -> None:
        completed: list[object] = []
        sup = ExecutionSupervisor(
            StubBackend(),
            SafetyLimits(),
            on_action_completed=lambda r: completed.append(r),
        )
        sup.execute_plan(_make_plan(), _make_snapshot(), BotMode.FULL_BOT)
        assert len(completed) == 1


# ── Retry with real transient failures (M9) ────────────────────────────────


class _FlakeyHandler(ActionHandler):
    """Handler that fails pre_check on first N calls, then succeeds."""

    action_type = "_test_flakey"
    requires_confirmation = False
    is_critical = False

    def __init__(self, backend, max_fails: int = 1):
        super().__init__(backend)
        self._fail_count = 0
        self._max_fails = max_fails

    def pre_check(self, plan, snapshot):
        if self._fail_count < self._max_fails:
            self._fail_count += 1
            return CheckResult(passed=False, message="transient failure")
        return CheckResult(passed=True, message="ok")

    def execute(self, plan, snapshot):
        pass

    def post_check(self, plan, snapshot):
        return CheckResult(passed=True, message="done")


register_handler(_FlakeyHandler)


class TestRetryReal:
    def test_retry_succeeds_after_transient_failure(self) -> None:
        config = SupervisorConfig(max_retries=2, retry_delay_seconds=0.0)
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits(), config=config)
        plan = _make_plan("_test_flakey")
        result = sup.execute_plan(plan, _make_snapshot(), BotMode.FULL_BOT)
        assert result.success is True
        assert result.message == "Azione completata."

    def test_retry_exhausted_returns_failure(self) -> None:
        config = SupervisorConfig(max_retries=0, retry_delay_seconds=0.0)
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits(), config=config)
        plan = _make_plan("_test_flakey")
        result = sup.execute_plan(plan, _make_snapshot(), BotMode.FULL_BOT)
        assert result.success is False
        assert "transient" in result.message.lower() or "pre-check" in result.message.lower()


# ── Timeout enforcement (M9) ───────────────────────────────────────────────


class _SlowHandler(ActionHandler):
    """Handler whose execute() sleeps longer than timeout."""

    action_type = "_test_slow"
    requires_confirmation = False
    is_critical = False

    def pre_check(self, plan, snapshot):
        return CheckResult(passed=True, message="ok")

    def execute(self, plan, snapshot):
        time.sleep(5)

    def post_check(self, plan, snapshot):
        return CheckResult(passed=True, message="done")


register_handler(_SlowHandler)


class TestTimeout:
    def test_timeout_triggers_emergency_stop(self) -> None:
        config = SupervisorConfig(action_timeout_seconds=0.2, max_retries=0, retry_delay_seconds=0.0)
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits(), config=config)
        plan = _make_plan("_test_slow")
        result = sup.execute_plan(plan, _make_snapshot(), BotMode.FULL_BOT)
        assert result.success is False
        assert sup.state == ExecutionState.EMERGENCY_STOP


# ── Confirmation gating (M9) ───────────────────────────────────────────────


class TestConfirmationGating:
    def test_semi_bot_blocks_confirmation_required(self) -> None:
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits())
        plan = _make_plan("military_recruit", requires_confirmation=True)
        result = sup.execute_plan(plan, _make_snapshot(), BotMode.SEMI_BOT)
        assert result.success is False
        assert result.pre_check.message == "awaiting_confirmation"

    def test_full_bot_skips_confirmation(self) -> None:
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits())
        plan = _make_plan("military_recruit", requires_confirmation=True)
        result = sup.execute_plan(plan, _make_snapshot(), BotMode.FULL_BOT)
        assert result.success is True

    def test_assist_mode_blocks_confirmation_required(self) -> None:
        sup = ExecutionSupervisor(StubBackend(), SafetyLimits())
        plan = _make_plan("military_recruit", requires_confirmation=True)
        result = sup.execute_plan(plan, _make_snapshot(), BotMode.ASSIST)
        assert result.success is False
        assert result.pre_check.message == "awaiting_confirmation"


# ── Safety limits (M9) ─────────────────────────────────────────────────────


class TestSafetyLimits:
    def test_recruit_blocked_when_limit_zero(self) -> None:
        safety = SafetyLimits(max_recruits_per_cycle=0)
        sup = ExecutionSupervisor(StubBackend(), safety)
        plan = _make_plan("military_recruit")
        result = sup.execute_plan(plan, _make_snapshot(), BotMode.FULL_BOT)
        assert result.success is False
        assert "disabilitato" in result.message.lower()

    def test_high_risk_blocks_execution(self) -> None:
        safety = SafetyLimits(auto_pause_on_high_risk=True)
        sup = ExecutionSupervisor(StubBackend(), safety)
        snap = _make_snapshot()
        snap.risk.coalition = 0.90
        plan = _make_plan("military_recruit")
        result = sup.execute_plan(plan, snap, BotMode.FULL_BOT)
        assert result.success is False
        assert "rischio" in result.message.lower()

    def test_normal_risk_allows_execution(self) -> None:
        safety = SafetyLimits(auto_pause_on_high_risk=True)
        sup = ExecutionSupervisor(StubBackend(), safety)
        snap = _make_snapshot()
        snap.risk.coalition = 0.30
        plan = _make_plan("military_recruit")
        result = sup.execute_plan(plan, snap, BotMode.FULL_BOT)
        assert result.success is True


# ── Crash hardening: callback exceptions don't propagate (M9) ──────────────


class TestCallbackCrashHardening:
    def test_crashing_on_state_changed_does_not_propagate(self) -> None:
        def bad_callback(state):
            raise RuntimeError("callback exploded")

        sup = ExecutionSupervisor(
            StubBackend(), SafetyLimits(), on_state_changed=bad_callback
        )
        # Should not raise — exception is swallowed and logged
        result = sup.execute_plan(_make_plan(), _make_snapshot(), BotMode.FULL_BOT)
        assert result.success is True

    def test_crashing_on_action_started_does_not_propagate(self) -> None:
        def bad_callback(plan):
            raise ValueError("started callback exploded")

        sup = ExecutionSupervisor(
            StubBackend(), SafetyLimits(), on_action_started=bad_callback
        )
        result = sup.execute_plan(_make_plan(), _make_snapshot(), BotMode.FULL_BOT)
        assert result.success is True

    def test_crashing_on_action_completed_does_not_propagate(self) -> None:
        def bad_callback(result):
            raise TypeError("completed callback exploded")

        sup = ExecutionSupervisor(
            StubBackend(), SafetyLimits(), on_action_completed=bad_callback
        )
        result = sup.execute_plan(_make_plan(), _make_snapshot(), BotMode.FULL_BOT)
        assert result.success is True


# ── Handler exception isolation (M9) ───────────────────────────────────────


class _CrashingExecuteHandler(ActionHandler):
    """Handler whose execute() raises an unexpected exception."""

    action_type = "_test_crashing_execute"
    requires_confirmation = False
    is_critical = False

    def pre_check(self, plan, snapshot):
        return CheckResult(passed=True, message="ok")

    def execute(self, plan, snapshot):
        raise RuntimeError("unexpected crash in execute")

    def post_check(self, plan, snapshot):
        return CheckResult(passed=True, message="done")


register_handler(_CrashingExecuteHandler)


class TestHandlerExceptionIsolation:
    def test_execute_exception_returns_failure_not_raises(self) -> None:
        sup = ExecutionSupervisor(
            StubBackend(), SafetyLimits(),
            config=SupervisorConfig(max_retries=0, retry_delay_seconds=0.0),
        )
        plan = _make_plan("_test_crashing_execute")
        result = sup.execute_plan(plan, _make_snapshot(), BotMode.FULL_BOT)
        assert result.success is False
        assert "crash" in result.message.lower() or "errore" in result.message.lower()
