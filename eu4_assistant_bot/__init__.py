"""EU4 Assistant + Bot core package (M1 foundation)."""

from .config import AppConfig, BotMode, DecisionThresholds, RiskProfile
from .decision_engine import DecisionEngine, Recommendation, RiskAlerts, RiskCode, RiskReason
from .executor import ActionExecutor, ExecutionResult
from .models import ActionPlan, GameSnapshot
from .save_adapter import SaveAdapterError, SaveSnapshotAdapter
from .state_reader import SnapshotReadError, SnapshotReader

__all__ = [
    "AppConfig",
    "BotMode",
    "RiskProfile",
    "DecisionThresholds",
    "ActionExecutor",
    "ExecutionResult",
    "ActionPlan",
    "GameSnapshot",
    "DecisionEngine",
    "Recommendation",
    "RiskAlerts",
    "RiskCode",
    "RiskReason",
    "SnapshotReader",
    "SnapshotReadError",
    "SaveSnapshotAdapter",
    "SaveAdapterError",
]
