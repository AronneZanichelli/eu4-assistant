"""Tests for ActionExecutor — simulate() (M1-M7) and execute() (M8)."""

from eu4_assistant_bot.config import BotMode
from eu4_assistant_bot.executor import ActionExecutor
from eu4_assistant_bot.models import ActionPlan


# ── simulate() tests (unchanged) ──────────────────────────────────────────────

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


# ── execute() tests (M8) ───────────────────────────────────────────────────────

def _make_plan(action_type: str = "economy_stabilize_budget") -> ActionPlan:
    return ActionPlan(
        id="test:80",
        action_type=action_type,
        priority=0.8,
        confidence=0.75,
        expected_outcome={"target_metric": "monthly_balance", "target_above": 0.0},
        requires_confirmation=True,
    )


def test_execute_assist_mode_returns_advisory() -> None:
    """In ASSIST mode, execute() logs advice without game interaction."""
    out = ActionExecutor().execute([_make_plan()], mode=BotMode.ASSIST)

    assert len(out) == 1
    assert out[0].status == "advisory"
    assert out[0].reason == "assist_mode_advisory_only"


def test_execute_semi_bot_mode_without_pyautogui() -> None:
    """In SEMI_BOT mode without pyautogui, execute() returns executed_no_pause."""
    # pyautogui may or may not be installed in CI; either status is acceptable
    out = ActionExecutor().execute([_make_plan()], mode=BotMode.SEMI_BOT)

    assert len(out) == 1
    assert out[0].status in ("executed", "executed_no_pause")
    assert out[0].action_type == "economy_stabilize_budget"


def test_execute_full_bot_mode_without_pyautogui() -> None:
    """FULL_BOT behaves identically to SEMI_BOT for M8 MVP."""
    out = ActionExecutor().execute([_make_plan()], mode=BotMode.FULL_BOT)

    assert len(out) == 1
    assert out[0].status in ("executed", "executed_no_pause")


def test_execute_returns_result_per_plan() -> None:
    plans = [_make_plan("economy_stabilize_budget"), _make_plan("military_recover_manpower")]

    out = ActionExecutor().execute(plans, mode=BotMode.ASSIST)

    assert len(out) == 2
    assert {r.action_type for r in out} == {"economy_stabilize_budget", "military_recover_manpower"}


def test_execute_simulated_effects_preserved() -> None:
    """execute() should include simulated_effects for UI compatibility."""
    out = ActionExecutor().execute([_make_plan()], mode=BotMode.ASSIST)

    assert "target_metric" in out[0].simulated_effects
    assert out[0].simulated_effects["projected_direction"] == "up"


def test_execute_confidence_preserved() -> None:
    plan = _make_plan()
    out = ActionExecutor().execute([plan], mode=BotMode.ASSIST)

    assert out[0].confidence == plan.confidence


def test_pause_game_returns_bool() -> None:
    """_pause_game() must always return a bool (True if sent, False on error)."""
    result = ActionExecutor._pause_game()

    assert isinstance(result, bool)
