"""Execution subpackage — real action execution via GUI automation."""

from .action_handler import (
    ActionHandler,
    CheckResult,
    HandlerResult,
    get_handler,
    register_handler,
)
from .input_backend import InputBackend, PyAutoGuiBackend, StubBackend
from .supervisor import ExecutionState, ExecutionSupervisor, SupervisorConfig

__all__ = [
    "ActionHandler",
    "CheckResult",
    "HandlerResult",
    "ExecutionState",
    "ExecutionSupervisor",
    "SupervisorConfig",
    "InputBackend",
    "PyAutoGuiBackend",
    "StubBackend",
    "get_handler",
    "register_handler",
]
