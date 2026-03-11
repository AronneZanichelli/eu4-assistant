from eu4_assistant_bot.config import BotMode
from eu4_assistant_bot.executor import ActionExecutor
from eu4_assistant_bot.models import ActionPlan


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
