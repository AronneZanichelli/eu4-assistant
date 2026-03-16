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
from ..execution.supervisor import ExecutionState
from ..models import ActionPlan, GameSnapshot
from .advisor_panel import AdvisorPanel
from .confirmation_dialog import ConfirmationDialog
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
    execution_started = pyqtSignal(str)           # action description
    execution_completed = pyqtSignal(object)       # HandlerResult
    execution_state_changed = pyqtSignal(str)     # ExecutionState value

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
        self.execution_started.connect(self._on_execution_started)
        self.execution_completed.connect(self._on_execution_completed)
        self.execution_state_changed.connect(self._on_execution_state_changed)

        # Action plan storage for execute flow
        self._current_plans: list[ActionPlan] = []

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

    # ── Execution slots ──────────────────────────────────────────────────

    def set_action_plans(self, plans: list[ActionPlan]) -> None:
        """Store latest action plans for execute flow."""
        self._current_plans = list(plans)

    @pyqtSlot(str)
    def _on_execution_started(self, description: str) -> None:
        self.advisor.show_execution_banner(description)
        self.log.add_entry(LogLevel.ACTION, f"Esecuzione: {description}")

    @pyqtSlot(object)
    def _on_execution_completed(self, result: object) -> None:
        self.advisor.hide_execution_banner()
        # result is a HandlerResult
        hr = result
        if hasattr(hr, "success"):
            status = "completata" if hr.success else "fallita"
            self.log.add_entry(
                LogLevel.ACTION if hr.success else LogLevel.ERROR,
                f"Azione {hr.action_type} {status}: {hr.message}",
            )
            if hasattr(hr, "is_critical") and hr.is_critical and hr.success:
                self.advisor.show_undo_available(hr.action_type)

    @pyqtSlot(str)
    def _on_execution_state_changed(self, state_value: str) -> None:
        if state_value == ExecutionState.PAUSED_EU4:
            self.advisor.show_eu4_paused()
        elif state_value == ExecutionState.IDLE:
            self.advisor.hide_execution_banner()
        elif state_value == ExecutionState.EMERGENCY_STOP:
            self.advisor.hide_execution_banner()
            self.log.add_entry(LogLevel.ERROR, "Emergency stop attivato")

    def show_confirmation_dialog(self, plan: ActionPlan) -> bool:
        """Show confirmation dialog and return True if user confirmed."""
        dialog = ConfirmationDialog(plan, parent=self)
        dialog.exec()
        return dialog.was_confirmed()

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
