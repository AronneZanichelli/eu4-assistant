"""Tests for the simulated ActionExecutor."""

from eu4_assistant_bot.config import BotMode
from eu4_assistant_bot.executor import ActionExecutor
from eu4_assistant_bot.models import ActionPlan, GameSnapshot


def _recruit_plan(**overrides) -> ActionPlan:
    defaults = dict(
        id="e:1",
        action_type="military_recruit",
        priority=0.8,
        confidence=0.7,
        requires_confirmation=False,
    )
    defaults.update(overrides)
    return ActionPlan(**defaults)


def _snap_with_manpower(manpower: int = 5000, force_limit: int = 20) -> GameSnapshot:
    snap = GameSnapshot.empty("FRA")
    snap.military.manpower = manpower
    snap.military.force_limit = force_limit
    return snap


# ── simulate() tests (M2 legacy, unchanged) ────────────────────────────────


def test_simulate_skips_confirmation_in_assist_mode() -> None:
    plans = [
        ActionPlan(
            id="a:90",
            action_type="economy_stabilize_budget",
            priority=0.9,
            confidence=0.8,
            expected_outcome={"target_metric": "monthly_balance", "target_above": 0.0},
            requires_confirmation=True,
        )
    ]

    out = ActionExecutor().simulate(plans, mode=BotMode.ASSIST)

    assert len(out) == 1
    assert out[0].status == "skipped"
    assert out[0].reason == "confirmation_required_in_assist_mode"


def test_simulate_executes_in_semi_bot_mode() -> None:
    plans = [
        ActionPlan(
            id="m:80",
            action_type="military_recover_manpower",
            priority=0.8,
            confidence=0.75,
            expected_outcome={"target_metric": "manpower_ratio", "target_above": 0.2},
            requires_confirmation=True,
        )
    ]

    out = ActionExecutor().simulate(plans, mode=BotMode.SEMI_BOT)

    assert len(out) == 1
    assert out[0].status == "simulated_executed"
    assert out[0].simulated_effects["projected_direction"] == "up"


# ── execute() tests (M9) ───────────────────────────────────────────────────


def test_execute_success() -> None:
    executor = ActionExecutor()
    plan = _recruit_plan()
    snap = _snap_with_manpower(5000, 20)
    result = executor.execute(plan, snap, BotMode.FULL_BOT)
    assert result.status == "executed"
    assert result.plan_id == "e:1"
    assert result.action_type == "military_recruit"


def test_execute_failure_bad_precondition() -> None:
    executor = ActionExecutor()
    plan = _recruit_plan()
    snap = _snap_with_manpower(manpower=0, force_limit=20)
    result = executor.execute(plan, snap, BotMode.FULL_BOT)
    assert result.status == "failed"
    assert "Manpower" in result.reason


def test_execute_unknown_action() -> None:
    executor = ActionExecutor()
    plan = _recruit_plan(action_type="totally_unknown_action")
    snap = _snap_with_manpower()
    result = executor.execute(plan, snap, BotMode.FULL_BOT)
    assert result.status == "failed"
    assert "Nessun handler" in result.reason


def test_execute_awaiting_confirmation_in_semi_bot() -> None:
    executor = ActionExecutor()
    plan = _recruit_plan(requires_confirmation=True)
    snap = _snap_with_manpower()
    result = executor.execute(plan, snap, BotMode.SEMI_BOT)
    assert result.status == "awaiting_confirmation"
    assert result.reason == "Richiede conferma utente."
