"""Tests for concrete action handlers."""
from eu4_assistant_bot.execution.action_handler import get_handler, registered_action_types
from eu4_assistant_bot.execution.input_backend import StubBackend
from eu4_assistant_bot.models import (
    ActionPlan,
    ArmyState,
    ColonialState,
    EconomyState,
    GameSnapshot,
    MilitaryState,
    WarState,
)


def _make_plan(action_type: str) -> ActionPlan:
    return ActionPlan(
        id=f"test:{action_type}",
        action_type=action_type,
        priority=0.8,
        confidence=0.7,
    )


# ── Registration ──────────────────────────────────────────────────────────


def test_all_9_handlers_registered() -> None:
    types = registered_action_types()
    expected = {
        "military_recruit",
        "colonial_send_colonist",
        "diplomacy_reduce_coalition",
        "economy_stabilize_budget",
        "military_move_army",
        "military_siege",
        "military_retreat",
        "military_engage",
        "military_peace_gate",
    }
    # Test-registered handlers may also be here; check expected is a subset
    assert expected.issubset(set(types))


# ── RecruitTroopsHandler ─────────────────────────────────────────────────


class TestRecruitTroopsHandler:
    def test_pre_check_fails_no_manpower(self) -> None:
        backend = StubBackend()
        handler = get_handler("military_recruit", backend)
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.military.manpower = 0
        snap.military.force_limit = 20

        result = handler.pre_check(_make_plan("military_recruit"), snap)
        assert not result.passed
        assert "manpower" in result.message.lower()

    def test_pre_check_fails_at_force_limit(self) -> None:
        backend = StubBackend()
        handler = get_handler("military_recruit", backend)
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.military.manpower = 5000
        snap.military.force_limit = 10
        snap.military.armies = [
            ArmyState(id="1", composition={"infantry": 10}),
        ]

        result = handler.pre_check(_make_plan("military_recruit"), snap)
        assert not result.passed
        assert "force limit" in result.message.lower()

    def test_pre_check_passes(self) -> None:
        backend = StubBackend()
        handler = get_handler("military_recruit", backend)
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.military.manpower = 5000
        snap.military.force_limit = 20
        snap.military.armies = [
            ArmyState(id="1", composition={"infantry": 10}),
        ]

        result = handler.pre_check(_make_plan("military_recruit"), snap)
        assert result.passed

    def test_execute_makes_clicks(self) -> None:
        backend = StubBackend()
        handler = get_handler("military_recruit", backend)
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.military.manpower = 5000
        snap.military.force_limit = 20
        snap.military.armies = [
            ArmyState(id="1", composition={"infantry": 10}),
        ]

        handler.execute(_make_plan("military_recruit"), snap)
        # Should have: send_key('b'), locate_template, N clicks, send_key('escape')
        call_types = [c[0] for c in backend.calls]
        assert "send_key" in call_types
        assert "click" in call_types

    def test_full_run_success(self) -> None:
        backend = StubBackend()
        handler = get_handler("military_recruit", backend)
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.military.manpower = 5000
        snap.military.force_limit = 20
        snap.military.armies = [
            ArmyState(id="1", composition={"infantry": 10}),
        ]

        result = handler.run(_make_plan("military_recruit"), snap)
        assert result.success


# ── SendColonistHandler ──────────────────────────────────────────────────


class TestSendColonistHandler:
    def test_pre_check_fails_no_colonist(self) -> None:
        handler = get_handler("colonial_send_colonist", StubBackend())
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.colonial = ColonialState(colonists_free=0)

        result = handler.pre_check(_make_plan("colonial_send_colonist"), snap)
        assert not result.passed

    def test_pre_check_passes(self) -> None:
        handler = get_handler("colonial_send_colonist", StubBackend())
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.colonial = ColonialState(colonists_free=1)

        result = handler.pre_check(_make_plan("colonial_send_colonist"), snap)
        assert result.passed


# ── ReduceMaintenanceHandler ─────────────────────────────────────────────


class TestReduceMaintenanceHandler:
    def test_pre_check_fails_positive_balance(self) -> None:
        handler = get_handler("economy_stabilize_budget", StubBackend())
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.economy = EconomyState(income=15, expenses=10)

        result = handler.pre_check(_make_plan("economy_stabilize_budget"), snap)
        assert not result.passed

    def test_pre_check_passes_negative_balance(self) -> None:
        handler = get_handler("economy_stabilize_budget", StubBackend())
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.economy = EconomyState(income=8, expenses=12)

        result = handler.pre_check(_make_plan("economy_stabilize_budget"), snap)
        assert result.passed

    def test_execute_drags_slider(self) -> None:
        backend = StubBackend()
        handler = get_handler("economy_stabilize_budget", backend)
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.economy = EconomyState(income=8, expenses=12)

        handler.execute(_make_plan("economy_stabilize_budget"), snap)
        call_types = [c[0] for c in backend.calls]
        assert "drag" in call_types


# ── ImproveRelationsHandler ──────────────────────────────────────────────


class TestImproveRelationsHandler:
    def test_pre_check_fails_no_coalition_risk(self) -> None:
        handler = get_handler("diplomacy_reduce_coalition", StubBackend())
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.risk.coalition = 0.0

        result = handler.pre_check(_make_plan("diplomacy_reduce_coalition"), snap)
        assert not result.passed

    def test_pre_check_passes(self) -> None:
        handler = get_handler("diplomacy_reduce_coalition", StubBackend())
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.risk.coalition = 0.7

        result = handler.pre_check(_make_plan("diplomacy_reduce_coalition"), snap)
        assert result.passed


# ── Wartime stubs ────────────────────────────────────────────────────────


class TestWartimeHandlers:
    def _wartime_snapshot(self) -> GameSnapshot:
        snap = GameSnapshot.empty()
        snap.military = MilitaryState(
            force_limit=20,
            manpower=5000,
            armies=[ArmyState(id="1", name="Armee")],
            wars=[WarState(war_name="Test War", our_side="attacker", war_score=30.0)],
            at_war=True,
        )
        return snap

    def _peacetime_snapshot(self) -> GameSnapshot:
        snap = GameSnapshot.empty()
        snap.military.at_war = False
        return snap

    def test_move_army_pre_check_passes_at_war(self) -> None:
        handler = get_handler("military_move_army", StubBackend())
        assert handler is not None
        result = handler.pre_check(_make_plan("military_move_army"), self._wartime_snapshot())
        assert result.passed

    def test_move_army_pre_check_fails_peacetime(self) -> None:
        handler = get_handler("military_move_army", StubBackend())
        assert handler is not None
        result = handler.pre_check(_make_plan("military_move_army"), self._peacetime_snapshot())
        assert not result.passed

    def test_siege_pre_check_passes_at_war(self) -> None:
        handler = get_handler("military_siege", StubBackend())
        assert handler is not None
        result = handler.pre_check(_make_plan("military_siege"), self._wartime_snapshot())
        assert result.passed

    def test_retreat_pre_check_passes_at_war(self) -> None:
        handler = get_handler("military_retreat", StubBackend())
        assert handler is not None
        result = handler.pre_check(_make_plan("military_retreat"), self._wartime_snapshot())
        assert result.passed

    def test_engage_pre_check_passes_at_war(self) -> None:
        handler = get_handler("military_engage", StubBackend())
        assert handler is not None
        result = handler.pre_check(_make_plan("military_engage"), self._wartime_snapshot())
        assert result.passed

    def test_wartime_stubs_execute_without_error(self) -> None:
        snap = self._wartime_snapshot()
        for action_type in ("military_move_army", "military_siege", "military_retreat", "military_engage"):
            handler = get_handler(action_type, StubBackend())
            assert handler is not None
            result = handler.run(_make_plan(action_type), snap)
            assert result.success


# ── PeaceTreatyHandler ───────────────────────────────────────────────────


class TestPeaceTreatyHandler:
    def test_requires_confirmation(self) -> None:
        handler = get_handler("military_peace_gate", StubBackend())
        assert handler is not None
        assert handler.requires_confirmation is True
        assert handler.is_critical is True

    def test_pre_check_fails_peacetime(self) -> None:
        handler = get_handler("military_peace_gate", StubBackend())
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.military.at_war = False

        result = handler.pre_check(_make_plan("military_peace_gate"), snap)
        assert not result.passed

    def test_execute_raises_not_implemented(self) -> None:
        handler = get_handler("military_peace_gate", StubBackend())
        assert handler is not None
        snap = GameSnapshot.empty()
        snap.military.at_war = True
        snap.military.wars = [WarState(war_name="Test", our_side="attacker")]

        # run() should catch NotImplementedError gracefully
        result = handler.run(_make_plan("military_peace_gate"), snap)
        assert not result.success
        assert "non ancora implementata" in result.message
