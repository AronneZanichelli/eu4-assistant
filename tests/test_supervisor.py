"""Tests for ExecutionSupervisor."""
from eu4_assistant_bot.config import BotMode, SafetyLimits
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
