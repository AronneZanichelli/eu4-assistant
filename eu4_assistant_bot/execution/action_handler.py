"""Action handler ABC with registry and template-method execution."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..models import ActionPlan, GameSnapshot
from .input_backend import InputBackend

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CheckResult:
    """Result of a pre_check or post_check."""

    passed: bool
    message: str


@dataclass(slots=True)
class HandlerResult:
    """Full result of running an action handler."""

    success: bool
    action_type: str
    message: str
    pre_check: CheckResult
    post_check: CheckResult | None = None
    is_critical: bool = False
    undoable: bool = False


class ActionHandler(ABC):
    """Base class for all EU4 action handlers.

    Subclasses implement pre_check/execute/post_check.
    The `run()` template method orchestrates the full flow.
    """

    action_type: str = ""
    requires_confirmation: bool = False
    is_critical: bool = False

    def __init__(self, backend: InputBackend) -> None:
        self._backend = backend

    @abstractmethod
    def pre_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        """Verify the game state allows this action."""

    @abstractmethod
    def execute(self, plan: ActionPlan, snapshot: GameSnapshot) -> None:
        """Perform the actual GUI interaction."""

    @abstractmethod
    def post_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        """Verify the action had the expected effect."""

    def run(self, plan: ActionPlan, snapshot: GameSnapshot) -> HandlerResult:
        """Template method: pre_check -> execute -> post_check."""
        pre = self.pre_check(plan, snapshot)
        if not pre.passed:
            return HandlerResult(
                success=False,
                action_type=self.action_type,
                message=f"Pre-check fallito: {pre.message}",
                pre_check=pre,
                is_critical=self.is_critical,
            )

        try:
            self.execute(plan, snapshot)
        except NotImplementedError:
            return HandlerResult(
                success=False,
                action_type=self.action_type,
                message="Azione non ancora implementata.",
                pre_check=pre,
                is_critical=self.is_critical,
            )
        except Exception as exc:
            logger.exception("Execute failed for %s", self.action_type)
            return HandlerResult(
                success=False,
                action_type=self.action_type,
                message=f"Errore esecuzione: {exc}",
                pre_check=pre,
                is_critical=self.is_critical,
            )

        post = self.post_check(plan, snapshot)
        return HandlerResult(
            success=post.passed,
            action_type=self.action_type,
            message=post.message if not post.passed else "Azione completata.",
            pre_check=pre,
            post_check=post,
            is_critical=self.is_critical,
            undoable=self.is_critical,
        )


# ── Handler registry ────────────────────────────────────────────────────────

_HANDLER_REGISTRY: dict[str, type[ActionHandler]] = {}


def register_handler(cls: type[ActionHandler]) -> type[ActionHandler]:
    """Decorator to register a handler class by its action_type."""
    if cls.action_type:
        _HANDLER_REGISTRY[cls.action_type] = cls
    return cls


def get_handler(action_type: str, backend: InputBackend) -> ActionHandler | None:
    """Look up and instantiate a handler for the given action type."""
    cls = _HANDLER_REGISTRY.get(action_type)
    if cls is None:
        return None
    return cls(backend)


def registered_action_types() -> list[str]:
    """Return all registered action type strings."""
    return list(_HANDLER_REGISTRY.keys())
