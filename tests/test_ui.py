"""Tests for UI components (M5).

Tests run without a display server by using QApplication in offscreen mode.
"""
from __future__ import annotations

import os
import sys

# Force offscreen rendering so tests work in headless CI
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication

from eu4_assistant_bot.decision_engine import Recommendation, RiskAlerts, RiskReason
from eu4_assistant_bot.models import (
    EconomyState,
    GameSnapshot,
    MilitaryState,
    RiskState,
)
from eu4_assistant_bot.ui.dashboard_panel import DashboardPanel
from eu4_assistant_bot.ui.advisor_panel import AdvisorPanel
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

    def test_push_snapshot_updates_dashboard(self, qapp: QApplication) -> None:
        win = MainWindow()
        snap = _snap()
        # Direct slot call (simulating signal delivery)
        win._on_snapshot(snap)
        assert win.dashboard._lbl_country.text() == "FRA"
