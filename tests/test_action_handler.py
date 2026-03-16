"""Tests for ActionHandler ABC, registry, and template method."""
from eu4_assistant_bot.execution.action_handler import (
    ActionHandler,
    CheckResult,
    HandlerResult,
    get_handler,
    register_handler,
    registered_action_types,
)
from eu4_assistant_bot.execution.input_backend import StubBackend
from eu4_assistant_bot.models import ActionPlan, GameSnapshot


class _DummyHandler(ActionHandler):
    action_type = "__test_dummy__"

    def pre_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        return CheckResult(passed=True, message="ok")

    def execute(self, plan: ActionPlan, snapshot: GameSnapshot) -> None:
        self._backend.click(1, 2)

    def post_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        return CheckResult(passed=True, message="done")


class _FailingPreCheckHandler(ActionHandler):
    action_type = "__test_fail_pre__"

    def pre_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        return CheckResult(passed=False, message="not ready")

    def execute(self, plan: ActionPlan, snapshot: GameSnapshot) -> None:
        self._backend.click(0, 0)

    def post_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        return CheckResult(passed=True, message="done")


class _NotImplementedHandler(ActionHandler):
    action_type = "__test_not_impl__"

    def pre_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        return CheckResult(passed=True, message="ok")

    def execute(self, plan: ActionPlan, snapshot: GameSnapshot) -> None:
        raise NotImplementedError("Not implemented yet")

    def post_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        return CheckResult(passed=True, message="done")


# Register for testing
register_handler(_DummyHandler)
register_handler(_FailingPreCheckHandler)
register_handler(_NotImplementedHandler)


def _make_plan(action_type: str = "__test_dummy__") -> ActionPlan:
    return ActionPlan(
        id="test:1",
        action_type=action_type,
        priority=0.8,
        confidence=0.7,
    )


class TestRegistry:
    def test_get_handler_returns_instance(self) -> None:
        backend = StubBackend()
        handler = get_handler("__test_dummy__", backend)
        assert handler is not None
        assert isinstance(handler, _DummyHandler)

    def test_get_handler_returns_none_for_unknown(self) -> None:
        backend = StubBackend()
        assert get_handler("nonexistent_type", backend) is None

    def test_registered_action_types_contains_test(self) -> None:
        types = registered_action_types()
        assert "__test_dummy__" in types


class TestRunTemplateMethod:
    def test_successful_run(self) -> None:
        backend = StubBackend()
        handler = _DummyHandler(backend)
        result = handler.run(_make_plan(), GameSnapshot.empty())

        assert result.success is True
        assert result.action_type == "__test_dummy__"
        assert result.pre_check.passed is True
        assert result.post_check is not None
        assert result.post_check.passed is True
        assert ("click", (1, 2)) in backend.calls

    def test_pre_check_failure_skips_execute(self) -> None:
        backend = StubBackend()
        handler = _FailingPreCheckHandler(backend)
        result = handler.run(_make_plan("__test_fail_pre__"), GameSnapshot.empty())

        assert result.success is False
        assert "Pre-check" in result.message
        assert len(backend.calls) == 0  # execute never called

    def test_not_implemented_handler(self) -> None:
        backend = StubBackend()
        handler = _NotImplementedHandler(backend)
        result = handler.run(_make_plan("__test_not_impl__"), GameSnapshot.empty())

        assert result.success is False
        assert "non ancora implementata" in result.message
