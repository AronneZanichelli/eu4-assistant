"""Application configuration, bot modes and risk profiles.

All paths use ``default_factory`` so that ``Path.home()`` is resolved at
instantiation time, not at import time — this keeps the config testable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path


class BotMode(str, Enum):
    ASSIST = "assist"
    SEMI_BOT = "semi-bot"
    FULL_BOT = "full-bot"

    @property
    def display_label(self) -> str:
        """Human-facing label used in the UI and docs.

        The enum *value* (``assist`` / ``semi-bot`` / ``full-bot``) is the
        canonical CLI/config token; this property is the single source of truth
        for the display label so UI, CLI and docs agree.
        """
        return {
            BotMode.ASSIST: "Advisor",
            BotMode.SEMI_BOT: "Semi-bot",
            BotMode.FULL_BOT: "Full-bot",
        }[self]


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
    debt_to_income_threshold: float = 24.0  # percentage: 24.0 = debt is 24% of income
    manpower_ratio_threshold: float = 0.18
    rebels_risk_threshold: float = 0.60
    # M6 military thresholds
    army_strength_threshold: float = 0.50   # total regiments / force_limit below this → alert
    wartime_manpower_min: int = 10_000      # manpower floor during active wars

    def __post_init__(self) -> None:
        if not (0.0 <= self.coalition_risk_threshold <= 1.0):
            raise ValueError(
                f"coalition_risk_threshold must be in [0, 1], got {self.coalition_risk_threshold}"
            )
        if self.debt_to_income_threshold < 0:
            raise ValueError(
                f"debt_to_income_threshold must be >= 0, got {self.debt_to_income_threshold}"
            )
        if not (0.0 <= self.manpower_ratio_threshold <= 1.0):
            raise ValueError(
                f"manpower_ratio_threshold must be in [0, 1], got {self.manpower_ratio_threshold}"
            )
        if not (0.0 <= self.rebels_risk_threshold <= 1.0):
            raise ValueError(
                f"rebels_risk_threshold must be in [0, 1], got {self.rebels_risk_threshold}"
            )
        if not (0.0 <= self.army_strength_threshold <= 1.0):
            raise ValueError(
                f"army_strength_threshold must be in [0, 1], got {self.army_strength_threshold}"
            )
        if self.wartime_manpower_min < 0:
            raise ValueError(
                f"wartime_manpower_min must be >= 0, got {self.wartime_manpower_min}"
            )


RISK_PROFILE_PRESETS: dict[RiskProfile, DecisionThresholds] = {
    RiskProfile.SAFE: DecisionThresholds(
        coalition_risk_threshold=0.45,
        debt_to_income_threshold=14.0,
        manpower_ratio_threshold=0.28,
        rebels_risk_threshold=0.40,
        army_strength_threshold=0.70,
        wartime_manpower_min=20_000,
    ),
    RiskProfile.BALANCED: DecisionThresholds(),
    RiskProfile.AGGRESSIVE: DecisionThresholds(
        coalition_risk_threshold=0.80,
        debt_to_income_threshold=40.0,
        manpower_ratio_threshold=0.10,
        rebels_risk_threshold=0.75,
        army_strength_threshold=0.30,
        wartime_manpower_min=5_000,
    ),
}


# Recommendation categories the full-bot may be allowed to act on (design §8.5).
# Canonical set kept here so the params UI and persistence agree on one list.
_DEFAULT_CATEGORIES: tuple[str, ...] = (
    "military",
    "colonial",
    "economy",
    "diplomacy",
    "trade",
    "internal",
    "strategy",
)

_COLONIAL_MODES: frozenset[str] = frozenset({"autonomous", "target_list"})

_BOT_PARAMS_FILENAME = "bot_params.json"


@dataclass(slots=True)
class BotParams:
    """User-tunable full-bot parameters, persisted to ``bot_params.json`` (design §8.10).

    Holds the knobs the full-bot params panel edits: active mode, risk profile,
    budget/recruit limits, enabled action categories, colonial sub-mode, and the
    two configurable alert thresholds (coalition / manpower). Persisted between
    sessions; persistence is deliberately Qt-free so it is testable headless.
    """

    mode: BotMode = BotMode.ASSIST
    risk_profile: RiskProfile = RiskProfile.BALANCED
    max_monthly_spend_ratio: float = 0.35
    max_recruits_per_cycle: int = 8
    enabled_categories: list[str] = field(default_factory=lambda: list(_DEFAULT_CATEGORIES))
    colonial_mode: str = "autonomous"
    coalition_risk_threshold: float = 0.65
    manpower_ratio_threshold: float = 0.18

    def __post_init__(self) -> None:
        if not (0.0 <= self.max_monthly_spend_ratio <= 1.0):
            raise ValueError(
                f"max_monthly_spend_ratio must be in [0, 1], got {self.max_monthly_spend_ratio}"
            )
        if self.max_recruits_per_cycle < 0:
            raise ValueError(
                f"max_recruits_per_cycle must be >= 0, got {self.max_recruits_per_cycle}"
            )
        if not (0.0 <= self.coalition_risk_threshold <= 1.0):
            raise ValueError(
                f"coalition_risk_threshold must be in [0, 1], got {self.coalition_risk_threshold}"
            )
        if not (0.0 <= self.manpower_ratio_threshold <= 1.0):
            raise ValueError(
                f"manpower_ratio_threshold must be in [0, 1], got {self.manpower_ratio_threshold}"
            )
        if self.colonial_mode not in _COLONIAL_MODES:
            raise ValueError(
                f"colonial_mode must be one of {sorted(_COLONIAL_MODES)}, got {self.colonial_mode!r}"
            )

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "risk_profile": self.risk_profile.value,
            "max_monthly_spend_ratio": self.max_monthly_spend_ratio,
            "max_recruits_per_cycle": self.max_recruits_per_cycle,
            "enabled_categories": list(self.enabled_categories),
            "colonial_mode": self.colonial_mode,
            "coalition_risk_threshold": self.coalition_risk_threshold,
            "manpower_ratio_threshold": self.manpower_ratio_threshold,
        }

    def save(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / _BOT_PARAMS_FILENAME).write_text(
            json.dumps(self.to_dict(), indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, data_dir: Path) -> "BotParams":
        """Load params from ``data_dir``; return defaults if absent or corrupt."""
        path = data_dir / _BOT_PARAMS_FILENAME
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            return cls()
        defaults = cls()
        try:
            return cls(
                mode=BotMode(data.get("mode", defaults.mode.value)),
                risk_profile=RiskProfile(data.get("risk_profile", defaults.risk_profile.value)),
                max_monthly_spend_ratio=float(
                    data.get("max_monthly_spend_ratio", defaults.max_monthly_spend_ratio)
                ),
                max_recruits_per_cycle=int(
                    data.get("max_recruits_per_cycle", defaults.max_recruits_per_cycle)
                ),
                enabled_categories=list(data.get("enabled_categories", defaults.enabled_categories)),
                colonial_mode=str(data.get("colonial_mode", defaults.colonial_mode)),
                coalition_risk_threshold=float(
                    data.get("coalition_risk_threshold", defaults.coalition_risk_threshold)
                ),
                manpower_ratio_threshold=float(
                    data.get("manpower_ratio_threshold", defaults.manpower_ratio_threshold)
                ),
            )
        except (ValueError, TypeError):
            return cls()


@dataclass(slots=True)
class AppConfig:
    mode: BotMode = BotMode.ASSIST
    risk_profile: RiskProfile = RiskProfile.BALANCED
    eu4_install_path: Path = field(default_factory=lambda: Path.home() / "Games" / "Europa Universalis IV")
    eu4_documents_path: Path = field(default_factory=lambda: Path.home() / "Documents" / "Paradox Interactive" / "Europa Universalis IV")
    active_mods_path: Path = field(default_factory=lambda: Path.home() / "Documents" / "Paradox Interactive" / "Europa Universalis IV" / "dlc_load.json")
    log_level: str = "INFO"
    data_dir: Path = field(default_factory=lambda: Path.home() / ".eu4-assistant")
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
