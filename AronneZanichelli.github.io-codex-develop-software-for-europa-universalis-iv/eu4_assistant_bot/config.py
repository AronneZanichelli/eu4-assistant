from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path


class BotMode(str, Enum):
    ASSIST = "assist"
    SEMI_BOT = "semi-bot"
    FULL_BOT = "full-bot"


class RiskProfile(str, Enum):
    SAFE = "safe"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass(slots=True)
class SafetyLimits:
    max_monthly_spend_ratio: float = 0.35
    max_recruits_per_cycle: int = 8
    auto_pause_on_high_risk: bool = True


@dataclass(slots=True)
class DecisionThresholds:
    coalition_risk_threshold: float = 0.65
    debt_to_income_threshold: float = 24.0
    manpower_ratio_threshold: float = 0.18
    rebels_risk_threshold: float = 0.60


RISK_PROFILE_PRESETS: dict[RiskProfile, DecisionThresholds] = {
    RiskProfile.SAFE: DecisionThresholds(
        coalition_risk_threshold=0.45,
        debt_to_income_threshold=14.0,
        manpower_ratio_threshold=0.28,
        rebels_risk_threshold=0.40,
    ),
    RiskProfile.BALANCED: DecisionThresholds(),
    RiskProfile.AGGRESSIVE: DecisionThresholds(
        coalition_risk_threshold=0.80,
        debt_to_income_threshold=40.0,
        manpower_ratio_threshold=0.10,
        rebels_risk_threshold=0.75,
    ),
}


@dataclass(slots=True)
class AppConfig:
    mode: BotMode = BotMode.ASSIST
    risk_profile: RiskProfile = RiskProfile.BALANCED
    eu4_install_path: Path = Path.home() / "Games" / "Europa Universalis IV"
    eu4_documents_path: Path = Path.home() / "Documents" / "Paradox Interactive" / "Europa Universalis IV"
    active_mods_path: Path = Path.home() / "Documents" / "Paradox Interactive" / "Europa Universalis IV" / "dlc_load.json"
    log_level: str = "INFO"
    data_dir: Path = Path(".eu4-assistant")
    safety: SafetyLimits = field(default_factory=SafetyLimits)
    decision: DecisionThresholds = field(default_factory=DecisionThresholds)

    def bootstrap_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "logs").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "snapshots").mkdir(parents=True, exist_ok=True)


MODE_PRESETS: dict[BotMode, SafetyLimits] = {
    BotMode.ASSIST: SafetyLimits(max_monthly_spend_ratio=0.20, max_recruits_per_cycle=0),
    BotMode.SEMI_BOT: SafetyLimits(max_monthly_spend_ratio=0.35, max_recruits_per_cycle=8),
    BotMode.FULL_BOT: SafetyLimits(max_monthly_spend_ratio=0.50, max_recruits_per_cycle=12),
}


def build_config(mode: BotMode = BotMode.ASSIST, risk_profile: RiskProfile = RiskProfile.BALANCED) -> AppConfig:
    config = AppConfig(
        mode=mode,
        risk_profile=risk_profile,
        safety=replace(MODE_PRESETS[mode]),
        decision=replace(RISK_PROFILE_PRESETS[risk_profile]),
    )
    config.bootstrap_dirs()
    return config
