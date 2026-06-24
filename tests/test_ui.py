"""Tests for UI components (M5).

Tests run without a display server by using QApplication in offscreen mode.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Force offscreen rendering so tests work in headless CI
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication

from eu4_assistant_bot.config import BotMode, BotParams, RiskProfile
from eu4_assistant_bot.decision_engine import Recommendation, RiskAlerts, RiskReason
from eu4_assistant_bot.models import (
    ActionPlan,
    EconomyState,
    GameSnapshot,
    MilitaryState,
    RiskState,
)
from eu4_assistant_bot.ui.dashboard_panel import DashboardPanel
from eu4_assistant_bot.ui.advisor_panel import AdvisorPanel, BotState
from eu4_assistant_bot.ui.log_panel import LogLevel, LogPanel
from eu4_assistant_bot.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    """Create a single QApplication for all UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def _snap() -> GameSnapshot:
    snap = GameSnapshot.empty("FRA")
    snap.eu4_date = "1470.3.15"
    snap.stability = 2
    snap.prestige = 45.0
    snap.legitimacy = 92.0
    snap.economy = EconomyState(treasury=1200.0, income=30.5, expenses=22.0, debt=100.0)
    snap.military = MilitaryState(force_limit=40, manpower=25000)
    snap.risk = RiskState(coalition=0.3, rebels=0.2)
    return snap


def _recs() -> list[Recommendation]:
    return [
        Recommendation(title="Espansione", rationale="Ok.", priority=0.78, category="strategy"),
        Recommendation(title="Trade", rationale="Bene.", priority=0.72, category="economy"),
    ]


def _alerts(coalition: bool = False, debt: bool = False) -> RiskAlerts:
    return RiskAlerts(
        coalition_risk=coalition,
        debt_risk=debt,
        manpower_risk=False,
        rebels_risk=False,
        reasons=[],
    )


class TestDashboardPanel:
    def test_update_snapshot(self, qapp: QApplication) -> None:
        panel = DashboardPanel()
        snap = _snap()
        panel.update_snapshot(snap)
        assert panel._lbl_country.text() == "FRA"
        assert panel._lbl_date.text() == "1470.3.15"
        assert "2" in panel._lbl_stability.text()
        assert "45" in panel._lbl_prestige.text()

    def test_manpower_bar(self, qapp: QApplication) -> None:
        panel = DashboardPanel()
        snap = _snap()
        panel.update_snapshot(snap)
        assert panel._bar_manpower.value() == 25000
        assert panel._bar_manpower.maximum() == 40000


class TestAdvisorPanel:
    def test_update_recommendations(self, qapp: QApplication) -> None:
        panel = AdvisorPanel()
        panel.update_recommendations(_recs())
        assert panel._cards[0]._lbl_title.text() == "Espansione"
        assert panel._cards[1]._lbl_title.text() == "Trade"
        assert not panel._cards[2].isVisible()

    def test_alert_badges(self, qapp: QApplication) -> None:
        panel = AdvisorPanel()
        panel.update_alerts(_alerts(coalition=True))
        # Coalition badge should be active (red background)
        style = panel._alert_labels["coalition"].styleSheet()
        assert "#b22" in style
        # Debt badge should be inactive
        style_debt = panel._alert_labels["debt"].styleSheet()
        assert "#333" in style_debt

    def test_mode_combo_emits_mode_changed(self, qapp: QApplication) -> None:
        """Selecting a mode in the combo emits mode_changed with the BotMode."""
        panel = AdvisorPanel()
        received: list[BotMode] = []
        panel.mode_changed.connect(received.append)
        idx = panel._mode_combo.findData(BotMode.FULL_BOT)
        panel._mode_combo.setCurrentIndex(idx)
        assert received == [BotMode.FULL_BOT]

    def test_select_mode_syncs_combo_without_emitting(self, qapp: QApplication) -> None:
        """Programmatic select_mode updates the combo but does not emit (no loop)."""
        panel = AdvisorPanel()
        received: list[BotMode] = []
        panel.mode_changed.connect(received.append)
        panel.select_mode(BotMode.SEMI_BOT)
        assert received == []
        assert panel._mode_combo.currentData() == BotMode.SEMI_BOT

    def test_default_bot_state_is_off(self, qapp: QApplication) -> None:
        panel = AdvisorPanel()
        assert panel._bot_state == BotState.OFF

    def test_set_bot_state_active(self, qapp: QApplication) -> None:
        panel = AdvisorPanel()
        panel.set_bot_state(BotState.ACTIVE)
        assert panel._bot_state == BotState.ACTIVE
        assert "Attivo" in panel._lbl_bot_state.text()

    def test_set_bot_state_error_shows_red(self, qapp: QApplication) -> None:
        panel = AdvisorPanel()
        panel.set_bot_state(BotState.ERROR)
        assert "Errore" in panel._lbl_bot_state.text()
        assert "#b22" in panel._lbl_bot_state.styleSheet()


class TestBotParamsPanel:
    def test_roundtrip(self, qapp: QApplication) -> None:
        """set_params then get_params returns an equal BotParams (minus mode, supplied)."""
        from eu4_assistant_bot.ui.bot_params_panel import BotParamsPanel

        panel = BotParamsPanel()
        bp = BotParams(
            mode=BotMode.FULL_BOT,
            risk_profile=RiskProfile.SAFE,
            max_monthly_spend_ratio=0.4,
            max_recruits_per_cycle=5,
            enabled_categories=["military", "colonial"],
            colonial_mode="target_list",
            coalition_risk_threshold=0.5,
            manpower_ratio_threshold=0.25,
        )
        panel.set_params(bp)
        assert panel.get_params(BotMode.FULL_BOT) == bp

    def test_threshold_editor_present(self, qapp: QApplication) -> None:
        """The coalition/manpower threshold editors round-trip too."""
        from eu4_assistant_bot.ui.bot_params_panel import BotParamsPanel

        panel = BotParamsPanel()
        panel.set_params(BotParams(coalition_risk_threshold=0.33, manpower_ratio_threshold=0.44))
        out = panel.get_params(BotMode.ASSIST)
        assert out.coalition_risk_threshold == 0.33
        assert out.manpower_ratio_threshold == 0.44


class TestAdvisorBotParams:
    def test_advisor_exposes_bot_params_panel(self, qapp: QApplication) -> None:
        from eu4_assistant_bot.ui.bot_params_panel import BotParamsPanel

        panel = AdvisorPanel()
        assert isinstance(panel.bot_params, BotParamsPanel)


class TestLogPanel:
    def test_add_entry(self, qapp: QApplication) -> None:
        panel = LogPanel()
        panel.add_entry(LogLevel.ALERT, "Test alert")
        assert panel._list.count() == 1
        assert "ALERT" in panel._list.item(0).text()

    def test_filter_hides_entries(self, qapp: QApplication) -> None:
        panel = LogPanel()
        panel.add_entry(LogLevel.ALERT, "Alert 1")
        panel.add_entry(LogLevel.DECISION, "Dec 1")
        assert panel._list.count() == 2
        # Uncheck ALERT filter
        panel._filters[LogLevel.ALERT].setChecked(False)
        panel._apply_filters()
        assert panel._list.count() == 1
        assert "DECISION" in panel._list.item(0).text()


class TestMainWindow:
    def test_construction(self, qapp: QApplication) -> None:
        win = MainWindow()
        assert win.windowTitle() == "EU4 Assistant"
        assert win.dashboard is not None
        assert win.advisor is not None
        assert win.log is not None

    def test_toggle_visibility(self, qapp: QApplication) -> None:
        win = MainWindow()
        win.show()
        assert win.isVisible()
        win.toggle_visibility()
        assert not win.isVisible()
        win.toggle_visibility()
        assert win.isVisible()

    def test_toggle_requested_signal_toggles(self, qapp: QApplication) -> None:
        """The thread-safe toggle_requested signal drives toggle_visibility."""
        win = MainWindow()
        win.show()
        assert win.isVisible()
        win.toggle_requested.emit()
        assert not win.isVisible()
        win.toggle_requested.emit()
        assert win.isVisible()

    def test_push_snapshot_updates_dashboard(self, qapp: QApplication) -> None:
        win = MainWindow()
        snap = _snap()
        # Direct slot call (simulating signal delivery)
        win._on_snapshot(snap)
        assert win.dashboard._lbl_country.text() == "FRA"

    def test_set_mode_updates_label(self, qapp: QApplication) -> None:
        win = MainWindow()
        win.set_mode(BotMode.SEMI_BOT)
        assert win._mode == BotMode.SEMI_BOT
        assert "semi" in win.advisor._lbl_mode.text().lower()

    def test_push_plans_stores_plans(self, qapp: QApplication) -> None:
        win = MainWindow()
        plan = ActionPlan(
            id="test:80",
            action_type="economy_stabilize_budget",
            priority=0.8,
            confidence=0.75,
            expected_outcome={"target_metric": "monthly_balance", "target_above": 0.0},
            requires_confirmation=False,
        )
        win._on_plans([plan])
        assert win._current_plans == [plan]

    def test_execute_requested_assist_mode_noop(self, qapp: QApplication) -> None:
        win = MainWindow()
        plan = ActionPlan(
            id="test:80",
            action_type="economy_stabilize_budget",
            priority=0.8,
            confidence=0.75,
            expected_outcome={"target_metric": "monthly_balance", "target_above": 0.0},
            requires_confirmation=False,
        )
        win._on_plans([plan])
        win.set_mode(BotMode.ASSIST)
        initial_count = win.log._list.count()
        win._on_execute_requested("economy")
        # In ASSIST mode a decision log entry is added but no crash occurs
        assert win.log._list.count() == initial_count + 1

    def test_execute_requested_no_plans(self, qapp: QApplication) -> None:
        win = MainWindow()
        # No plans pushed — _current_plans is empty
        win._on_execute_requested("economy")
        assert win.log._list.count() == 1
        assert "Nessun piano" in win.log._list.item(0).text()

    def test_advisor_mode_change_updates_window_mode(self, qapp: QApplication) -> None:
        """The advisor mode selector is wired to MainWindow.set_mode."""
        win = MainWindow()
        win.advisor.mode_changed.emit(BotMode.FULL_BOT)
        assert win._mode == BotMode.FULL_BOT

    def test_set_mode_drives_bot_state(self, qapp: QApplication) -> None:
        win = MainWindow()
        win.set_mode(BotMode.FULL_BOT)
        assert win.advisor._bot_state == BotState.ACTIVE
        win.set_mode(BotMode.ASSIST)
        assert win.advisor._bot_state == BotState.OFF

    def test_reflect_bot_state_error_on_blocked(self, qapp: QApplication) -> None:
        from eu4_assistant_bot.executor import ExecutionResult

        win = MainWindow()
        win.set_mode(BotMode.FULL_BOT)
        win._reflect_bot_state(
            [ExecutionResult(plan_id="x", action_type="t", status="blocked", reason="r", confidence=0.5)]
        )
        assert win.advisor._bot_state == BotState.ERROR

    def test_botparams_persist_and_reload(self, qapp: QApplication, tmp_path: Path) -> None:
        win = MainWindow(data_dir=tmp_path)
        win.advisor.bot_params.set_params(BotParams(max_recruits_per_cycle=3))
        win.set_mode(BotMode.SEMI_BOT)
        win._save_bot_params()

        reloaded = MainWindow(data_dir=tmp_path)
        assert reloaded._mode == BotMode.SEMI_BOT
        assert reloaded.advisor.bot_params.get_params(reloaded._mode).max_recruits_per_cycle == 3
