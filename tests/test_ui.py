"""
Test UI M5 — headless, senza display reale.
Usa pytest-qt con QApplication offscreen.
"""
import pytest

pytest.importorskip("PyQt6", reason="PyQt6 non disponibile")

from PyQt6.QtWidgets import QApplication
from eu4_assistant_bot.models import (
    GameSnapshot, EconomyState, MilitaryState, RiskState,
    DiplomacyState, TechState, IdeasState,
)
from eu4_assistant_bot.decision_engine import DecisionEngine, RiskAlerts, Recommendation
from eu4_assistant_bot.ui.dashboard_panel import DashboardPanel
from eu4_assistant_bot.ui.advisor_panel import AdvisorPanel
from eu4_assistant_bot.ui.log_panel import LogPanel


def _snap() -> GameSnapshot:
    snap = GameSnapshot.empty("POR")
    snap.eu4_date = "1460.06.01"
    snap.stability = 2
    snap.prestige = 45.0
    snap.legitimacy = 95.0
    snap.economy = EconomyState(treasury=200.0, income=18.0, expenses=12.0, debt=0.0)
    snap.military = MilitaryState(force_limit=30, manpower=22000)
    snap.risk = RiskState(coalition=0.1, rebels=0.1)
    snap.tech = TechState(adm_tech=5, dip_tech=5, mil_tech=6)
    snap.ideas = IdeasState(completed_groups=["exploration_ideas"])
    return snap


@pytest.fixture(scope="module")
def qapp():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app


def test_dashboard_panel_updates(qapp):
    panel = DashboardPanel()
    panel.update_snapshot(_snap())
    assert panel._tag_label.text() == "POR"
    assert "1460" in panel._date_label.text()


def test_dashboard_panel_shows_stability(qapp):
    panel = DashboardPanel()
    panel.update_snapshot(_snap())
    assert "+2" in panel._stability_label.text()


def test_advisor_panel_shows_recommendations(qapp):
    panel = AdvisorPanel()
    engine = DecisionEngine()
    snap = _snap()
    recs = engine.recommend(snap)
    panel.update_recommendations(recs)
    # At least one card visible
    cards = [panel._cards_layout.itemAt(i).widget()
             for i in range(panel._cards_layout.count())
             if panel._cards_layout.itemAt(i).widget()]
    assert len(cards) >= 1


def test_advisor_panel_shows_alerts(qapp):
    panel = AdvisorPanel()
    risky_snap = _snap()
    risky_snap.risk = RiskState(coalition=0.9, rebels=0.9)
    engine = DecisionEngine()
    risks = engine.evaluate_risks(risky_snap)
    panel.update_alerts(risks)
    # Badges should be added (alert_lbl hidden)
    assert not panel._alert_lbl.isVisible()


def test_advisor_panel_no_alerts(qapp):
    panel = AdvisorPanel()
    safe_snap = _snap()
    engine = DecisionEngine()
    risks = engine.evaluate_risks(safe_snap)
    panel.update_alerts(risks)
    # When no alerts active, label text should indicate no alerts
    assert "nessun" in panel._alert_lbl.text().lower()


def test_advisor_pause_banner(qapp):
    panel = AdvisorPanel()
    assert panel._pause_banner.text() == ""
    panel.show_pause_banner("Test pausa")
    assert "Test pausa" in panel._pause_banner.text()
    panel.hide_pause_banner()
    # After hide, banner is hidden (text preserved but widget hidden)
    assert "Test pausa" in panel._pause_banner.text()


def test_log_panel_append(qapp):
    panel = LogPanel()
    panel.append("alert", "Test messaggio")
    assert len(panel._entries) == 1
    assert panel._entries[0]["category"] == "alert"


def test_log_panel_filter(qapp):
    panel = LogPanel()
    panel.append("alert", "messaggio alert")
    panel.append("decision", "messaggio decision")
    panel._filter.setCurrentText("Alert")
    # Feed should show only alert entry
    text = panel._feed.toPlainText()
    assert "alert" in text.lower()
    assert "decision" not in text.lower()
