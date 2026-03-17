"""EU4 Assistant + Bot — desktop companion for Europa Universalis IV.

Reads autosave files in real time, builds a typed game-state snapshot,
evaluates risks and generates contextual recommendations.  Optional
semi-bot and full-bot modes can execute actions via screen automation.
"""

__version__ = "0.5.0"


from .config import AppConfig, BotMode, DecisionThresholds, RiskProfile
from .decision_engine import DecisionEngine, Recommendation, RiskAlerts, RiskCode, RiskReason
from .executor import ActionExecutor, ExecutionResult
from .extractor import StateExtractor
from .mod import ModBuilder, ModInstallResult, ModInstallStatus
from .models import (
    ActionPlan,
    ArmyState,
    ColonialState,
    DiplomacyState,
    EconomyState,
    GameSnapshot,
    IdeasState,
    MilitaryState,
    ProvinceState,
    RiskState,
    WarState,
    TechState,
    TradeNodeState,
)
from .parser import ClausewitzTextParser
from .save_adapter import SaveAdapterError, SaveSnapshotAdapter
from .save_unzipper import SaveFormatError, SaveUnzipper
from .state_reader import SnapshotReadError, SnapshotReader
from .pause_controller import PauseController, PauseEvent, PauseReason
from .watcher import FileWatcher, SaveEvent, SaveEventType

__all__ = [
    "AppConfig", "BotMode", "RiskProfile", "DecisionThresholds",
    "ActionExecutor", "ExecutionResult",
    "StateExtractor",
    "ModBuilder", "ModInstallResult", "ModInstallStatus",
    "ActionPlan", "GameSnapshot",
    "ArmyState", "ProvinceState", "TradeNodeState",
    "EconomyState", "MilitaryState", "DiplomacyState",
    "ColonialState", "RiskState", "WarState", "TechState", "IdeasState",
    "DecisionEngine", "Recommendation", "RiskAlerts", "RiskCode", "RiskReason",
    "SnapshotReader", "SnapshotReadError",
    "SaveSnapshotAdapter", "SaveAdapterError",
    "ClausewitzTextParser",
    "SaveUnzipper", "SaveFormatError",
    "PauseController", "PauseEvent", "PauseReason",
    "FileWatcher", "SaveEvent", "SaveEventType",
]
