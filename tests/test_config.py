"""Tests for AppConfig, build_config and risk profile presets."""

from pathlib import Path

import pytest

from eu4_assistant_bot.config import (
    AppConfig,
    BotMode,
    BotParams,
    RiskProfile,
    build_config,
)


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


# ── BotParams (full-bot persisted parameters, design §8.10) ──────────────────


def test_botparams_defaults() -> None:
    bp = BotParams()
    assert bp.mode == BotMode.ASSIST
    assert bp.risk_profile == RiskProfile.BALANCED
    assert bp.colonial_mode == "autonomous"
    assert "military" in bp.enabled_categories


def test_botparams_roundtrip(tmp_path: Path) -> None:
    bp = BotParams(
        mode=BotMode.FULL_BOT,
        risk_profile=RiskProfile.AGGRESSIVE,
        max_monthly_spend_ratio=0.5,
        max_recruits_per_cycle=12,
        enabled_categories=["military", "colonial"],
        colonial_mode="target_list",
        coalition_risk_threshold=0.7,
        manpower_ratio_threshold=0.2,
    )
    bp.save(tmp_path)
    assert BotParams.load(tmp_path) == bp


def test_botparams_load_missing_returns_defaults(tmp_path: Path) -> None:
    assert BotParams.load(tmp_path) == BotParams()


def test_botparams_load_corrupt_returns_defaults(tmp_path: Path) -> None:
    (tmp_path / "bot_params.json").write_text("{ not json", encoding="utf-8")
    assert BotParams.load(tmp_path) == BotParams()


def test_botparams_rejects_invalid_spend_ratio() -> None:
    with pytest.raises(ValueError):
        BotParams(max_monthly_spend_ratio=1.5)


def test_botparams_rejects_invalid_coalition_threshold() -> None:
    with pytest.raises(ValueError):
        BotParams(coalition_risk_threshold=2.0)


def test_botparams_rejects_unknown_colonial_mode() -> None:
    with pytest.raises(ValueError):
        BotParams(colonial_mode="nonsense")
