from pathlib import Path

from eu4_assistant_bot.config import AppConfig, BotMode, RiskProfile, build_config


def test_appconfig_data_dir_is_absolute() -> None:
    """data_dir should default to an absolute path under home, not a relative path."""
    config = AppConfig()
    assert config.data_dir.is_absolute()
    assert ".eu4-assistant" in str(config.data_dir)


def test_appconfig_paths_use_home(monkeypatch) -> None:
    """Path defaults should use Path.home(), evaluated at instantiation time."""
    fake_home = Path("/fake/home")
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
    config = AppConfig()
    assert str(config.eu4_install_path).startswith(str(fake_home))
    assert str(config.data_dir).startswith(str(fake_home))


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
