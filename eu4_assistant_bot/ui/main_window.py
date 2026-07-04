"""MainWindow — 3-column EU4 Assistant companion window (M5).

Layout: Dashboard (left) | Advisor (center) | Log (right)
Dark theme, F2 hotkey show/hide, position persists between sessions.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QWidget

from ..config import BotMode, BotParams
from ..decision_engine import Recommendation, RiskAlerts
from ..executor import ActionExecutor, ExecutionResult
from ..models import ActionPlan, GameSnapshot
from .advisor_panel import AdvisorPanel, BotState
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
    plans_received = pyqtSignal(object)            # list[ActionPlan]
    log_received = pyqtSignal(object, str)         # (LogLevel, message)
    toggle_requested = pyqtSignal()                # F2 global hotkey (thread-safe toggle)

    def __init__(self, parent: QWidget | None = None, data_dir: Path | None = None) -> None:
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
        self.plans_received.connect(self._on_plans)
        self.log_received.connect(self._on_log)
        self.toggle_requested.connect(self.toggle_visibility)
        self.advisor.execute_requested.connect(self._on_execute_requested)
        self.advisor.mode_changed.connect(self.set_mode)

        # ── M8: executor state ──
        self._executor: ActionExecutor = ActionExecutor()
        self._mode: BotMode = BotMode.ASSIST
        self._current_plans: list[ActionPlan] = []

        # ── Full-bot params persistence (design §8.10) ──
        self._data_dir = data_dir
        if data_dir is not None:
            params = BotParams.load(data_dir)
            self.advisor.bot_params.set_params(params)
            self.set_mode(params.mode)

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

    def push_plans(self, plans: list[ActionPlan]) -> None:
        """Thread-safe: store current action plans for execution."""
        self.plans_received.emit(plans)

    def push_log(self, level: LogLevel, message: str) -> None:
        """Thread-safe: emit signal to append a log entry from any thread."""
        self.log_received.emit(level, message)

    def set_mode(self, mode: BotMode) -> None:
        """Set execution mode, sync the selector, and refresh the bot-state indicator."""
        self._mode = mode
        self.advisor.select_mode(mode)
        self._sync_bot_state_to_mode()

    def _sync_bot_state_to_mode(self) -> None:
        """OFF in Advisor (passive); ACTIVE when a bot mode is selected."""
        state = BotState.OFF if self._mode == BotMode.ASSIST else BotState.ACTIVE
        self.advisor.set_bot_state(state)

    def _reflect_bot_state(self, results: list[ExecutionResult]) -> None:
        """Drive the bot-state indicator from execution results (design §5.5)."""
        if any(r.status in ("blocked", "error", "failed") for r in results):
            self.advisor.set_bot_state(BotState.ERROR)
        else:
            self._sync_bot_state_to_mode()

    def _save_bot_params(self) -> None:
        """Persist the current full-bot params + active mode to ``bot_params.json``."""
        if self._data_dir is None:
            return
        self.advisor.bot_params.get_params(self._mode).save(self._data_dir)

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

    @pyqtSlot(object)
    def _on_plans(self, plans: list[ActionPlan]) -> None:
        self._current_plans = plans

    @pyqtSlot(object, str)
    def _on_log(self, level: LogLevel, message: str) -> None:
        self.log.add_entry(level, message)

    @pyqtSlot(str)
    def _on_execute_requested(self, category: str) -> None:
        """Handle Esegui button click from any recommendation card."""
        if not self._current_plans:
            self.push_log(LogLevel.ALERT, "Nessun piano disponibile — attendi il prossimo salvataggio.")
            return

        if self._mode == BotMode.ASSIST:
            self.push_log(LogLevel.DECISION, f"Modalità Advisor: esecuzione disabilitata [{category}].")
            return

        # The confirmation gate is enforced inside execute(); the dialog is the
        # acknowledgement it calls back into (SEMI_BOT every action, FULL_BOT only
        # actions flagged requires_confirmation).
        results = self._executor.execute(
            self._current_plans, self._mode, confirm=self._confirm_plan
        )
        for result in results:
            if result.status == "blocked":
                self.push_log(LogLevel.DECISION, f"[{result.action_type}] esecuzione annullata (conferma negata).")
                continue
            level = LogLevel.ACTION if result.status in ("executed", "executed_no_pause", "advisory", "colonize_started") else LogLevel.ALERT
            self.push_log(level, f"[{result.action_type}] {result.status} — {result.reason}")
        self._reflect_bot_state(results)

    def _confirm_plan(self, plan: ActionPlan) -> bool:
        """Confirmation gate passed to ActionExecutor.execute() before a real action."""
        reply = QMessageBox.question(
            self,
            "Conferma esecuzione",
            f"Eseguire azione '{plan.action_type}' (priorità {plan.priority:.0%})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    # ── Window management ──────────────────────────────────────────────────

    @pyqtSlot()
    def toggle_visibility(self) -> None:
        """F2 hotkey handler: show/hide the window (thread-safe via toggle_requested)."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def closeEvent(self, event: "QCloseEvent") -> None:  # type: ignore[override]
        self._save_bot_params()
        self._settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)
