"""MainWindow — 3-column EU4 Assistant companion window (M5).

Layout: Dashboard (left) | Advisor (center) | Log (right)
Dark theme, F2 hotkey show/hide, position persists between sessions.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QWidget

from ..decision_engine import Recommendation, RiskAlerts
from ..models import GameSnapshot
from .advisor_panel import AdvisorPanel
from .dashboard_panel import DashboardPanel
from .log_panel import LogLevel, LogPanel

logger = logging.getLogger(__name__)

_DARK_STYLE = """
QWidget {
    background-color: #1e1e1e;
    color: #ddd;
    font-family: "Segoe UI", "Roboto", sans-serif;
}
QProgressBar {
    border: 1px solid #555;
    border-radius: 3px;
    text-align: center;
    background: #2a2a2a;
}
QProgressBar::chunk {
    background: #4a9;
    border-radius: 2px;
}
QPushButton {
    background: #333;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 4px 10px;
    color: #ddd;
}
QPushButton:hover { background: #444; }
QPushButton:pressed { background: #555; }
QPushButton:checked { background: #4a9; color: #111; }
QListWidget {
    background: #252525;
    border: 1px solid #444;
    border-radius: 4px;
}
"""


class MainWindow(QMainWindow):
    """EU4 Assistant companion window with 3-column layout.

    Signals
    -------
    snapshot_updated(GameSnapshot)
        Emitted by the pipeline when a new snapshot is ready.
    recommendations_updated(list)
        Emitted with top-3 recommendations.
    alerts_updated(RiskAlerts)
        Emitted with current risk alerts.
    """

    # Signals for thread-safe UI updates from pipeline thread
    snapshot_received = pyqtSignal(object)        # GameSnapshot
    recommendations_received = pyqtSignal(object)  # list[Recommendation]
    alerts_received = pyqtSignal(object)           # RiskAlerts

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("EU4 Assistant")
        self.setMinimumSize(1000, 600)
        self.setStyleSheet(_DARK_STYLE)

        # ── Central widget with 3-column layout ──
        central = QWidget()
        self.setCentralWidget(central)
        hlayout = QHBoxLayout(central)
        hlayout.setContentsMargins(4, 4, 4, 4)

        self.dashboard = DashboardPanel()
        self.advisor = AdvisorPanel()
        self.log = LogPanel()

        # Proportions: Dashboard ~25%, Advisor ~45%, Log ~30%
        hlayout.addWidget(self.dashboard, stretch=25)
        hlayout.addWidget(self.advisor, stretch=45)
        hlayout.addWidget(self.log, stretch=30)

        # ── Connect signals to slots ──
        self.snapshot_received.connect(self._on_snapshot)
        self.recommendations_received.connect(self._on_recommendations)
        self.alerts_received.connect(self._on_alerts)

        # ── Restore window geometry ──
        self._settings = QSettings("EU4Assistant", "MainWindow")
        geo = self._settings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)

    # ── Public API (called from pipeline thread via signals) ────────────────

    def push_snapshot(self, snap: GameSnapshot) -> None:
        """Thread-safe: emit signal to update UI from any thread."""
        self.snapshot_received.emit(snap)

    def push_recommendations(self, recs: list[Recommendation]) -> None:
        self.recommendations_received.emit(recs)

    def push_alerts(self, alerts: RiskAlerts) -> None:
        self.alerts_received.emit(alerts)

    def push_log(self, level: LogLevel, message: str) -> None:
        self.log.add_entry(level, message)

    # ── Slots ──────────────────────────────────────────────────────────────

    @pyqtSlot(object)
    def _on_snapshot(self, snap: GameSnapshot) -> None:
        self.dashboard.update_snapshot(snap)

    @pyqtSlot(object)
    def _on_recommendations(self, recs: list[Recommendation]) -> None:
        self.advisor.update_recommendations(recs)

    @pyqtSlot(object)
    def _on_alerts(self, alerts: RiskAlerts) -> None:
        self.advisor.update_alerts(alerts)

    # ── Window management ──────────────────────────────────────────────────

    def toggle_visibility(self) -> None:
        """F2 hotkey handler: show/hide the window."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def closeEvent(self, event: "QCloseEvent") -> None:  # type: ignore[override]
        self._settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)
