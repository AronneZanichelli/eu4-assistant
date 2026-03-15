"""EU4 Assistant + Bot core package."""

from .config import AppConfig, BotMode, DecisionThresholds, RiskProfile
from .decision_engine import DecisionEngine, Recommendation, RiskAlerts, RiskCode, RiskReason
from .executor import ActionExecutor, ExecutionResult
from .extractor import StateExtractor
from .mod import ModBuilder, ModInstallResult, ModInstallStatus
from .models import (
    ActionPlan,
    ColonialState,
    DiplomacyState,
    EconomyState,
    GameSnapshot,
    IdeasState,
    MilitaryState,
    RiskState,
    TechState,
)
from .parser import ClausewitzTextParser
from .save_adapter import SaveAdapterError, SaveSnapshotAdapter
from .save_unzipper import SaveFormatError, SaveUnzipper
from .state_reader import SnapshotReadError, SnapshotReader
from .watcher import FileWatcher, SaveEvent, SaveEventType

__all__ = [
    "AppConfig", "BotMode", "RiskProfile", "DecisionThresholds",
    "ActionExecutor", "ExecutionResult",
    "StateExtractor",
    "ModBuilder", "ModInstallResult", "ModInstallStatus",
    "ActionPlan", "GameSnapshot",
    "EconomyState", "MilitaryState", "DiplomacyState",
    "ColonialState", "RiskState", "TechState", "IdeasState",
    "DecisionEngine", "Recommendation", "RiskAlerts", "RiskCode", "RiskReason",
    "SnapshotReader", "SnapshotReadError",
    "SaveSnapshotAdapter", "SaveAdapterError",
    "ClausewitzTextParser",
    "SaveUnzipper", "SaveFormatError",
    "FileWatcher", "SaveEvent", "SaveEventType",
]
