"""Tests for PauseController (M5)."""
from __future__ import annotations

from eu4_assistant_bot.models import DiplomacyState, GameSnapshot, RiskState
from eu4_assistant_bot.pause_controller import PauseController, PauseEvent, PauseReason


def _snap(rebels: float = 0.0, active_wars: int = 0) -> GameSnapshot:
    """Build a minimal snapshot with risk.rebels and diplomacy.active_wars."""
    snap = GameSnapshot.empty("FRA")
    snap.risk = RiskState(rebels=rebels)
    snap.diplomacy = DiplomacyState(active_wars=active_wars)
    return snap


class TestPauseControllerRebels:
    def test_no_pause_below_threshold(self) -> None:
        keys: list[str] = []
        ctrl = PauseController(rebels_threshold=0.60, send_key=keys.append)
        result = ctrl.check(_snap(rebels=0.3))
        assert result is None
        assert keys == []

    def test_pause_on_rebels_above_threshold(self) -> None:
        keys: list[str] = []
        ctrl = PauseController(rebels_threshold=0.60, send_key=keys.append)
        result = ctrl.check(_snap(rebels=0.75))
        assert result is not None
        assert result.reason == PauseReason.REBELS_IMMINENT
        assert keys == ["space"]

    def test_no_spam_same_rebels_reason(self) -> None:
        """Second consecutive rebels check should not re-trigger."""
        keys: list[str] = []
        ctrl = PauseController(rebels_threshold=0.60, send_key=keys.append)
        ctrl.check(_snap(rebels=0.80))
        result2 = ctrl.check(_snap(rebels=0.80))
        assert result2 is None
        assert keys == ["space"]  # only one

    def test_re_triggers_after_clear(self) -> None:
        """After rebels drop and rise again, should trigger again."""
        keys: list[str] = []
        ctrl = PauseController(rebels_threshold=0.60, send_key=keys.append)
        ctrl.check(_snap(rebels=0.80))
        ctrl.check(_snap(rebels=0.20))  # clears
        result = ctrl.check(_snap(rebels=0.80))
        assert result is not None
        assert keys == ["space", "space"]


class TestPauseControllerWar:
    def test_no_pause_first_snapshot(self) -> None:
        """First snapshot has no baseline — should not trigger."""
        keys: list[str] = []
        ctrl = PauseController(send_key=keys.append)
        result = ctrl.check(_snap(active_wars=2))
        assert result is None

    def test_pause_on_new_war(self) -> None:
        keys: list[str] = []
        ctrl = PauseController(send_key=keys.append)
        ctrl.check(_snap(active_wars=0))  # baseline: peace
        result = ctrl.check(_snap(active_wars=1))  # new war declared
        assert result is not None
        assert result.reason == PauseReason.WAR_DECLARED
        assert keys == ["space"]

    def test_no_pause_same_wars(self) -> None:
        keys: list[str] = []
        ctrl = PauseController(send_key=keys.append)
        ctrl.check(_snap(active_wars=1))
        result = ctrl.check(_snap(active_wars=1))
        assert result is None
        assert keys == []

    def test_no_pause_when_war_ends(self) -> None:
        """War count decreasing (war ended) should NOT trigger pause."""
        keys: list[str] = []
        ctrl = PauseController(send_key=keys.append)
        ctrl.check(_snap(active_wars=2))
        result = ctrl.check(_snap(active_wars=1))  # war ended
        assert result is None
        assert keys == []


class TestPauseControllerCallback:
    def test_on_pause_callback_invoked(self) -> None:
        events: list[PauseEvent] = []
        ctrl = PauseController(
            rebels_threshold=0.50,
            on_pause=events.append,
            send_key=lambda k: None,
        )
        ctrl.check(_snap(rebels=0.70))
        assert len(events) == 1
        assert events[0].reason == PauseReason.REBELS_IMMINENT
