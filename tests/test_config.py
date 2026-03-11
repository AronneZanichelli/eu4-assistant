from eu4_assistant_bot.config import BotMode, RiskProfile, build_config


def test_build_config_applies_safe_risk_profile() -> None:
    config = build_config(BotMode.ASSIST, risk_profile=RiskProfile.SAFE)

    assert config.risk_profile == RiskProfile.SAFE
    assert config.decision.coalition_risk_threshold == 0.45
    assert config.decision.debt_to_income_threshold == 14.0


def test_build_config_applies_aggressive_risk_profile() -> None:
    config = build_config(BotMode.ASSIST, risk_profile=RiskProfile.AGGRESSIVE)

    assert config.risk_profile == RiskProfile.AGGRESSIVE
    assert config.decision.coalition_risk_threshold == 0.80
    assert config.decision.manpower_ratio_threshold == 0.10
