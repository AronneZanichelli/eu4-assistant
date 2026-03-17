from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QSettings, QSize, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow,
    QSplitter, QStatusBar, QWidget,
)

from ..decision_engine import DecisionEngine
from ..extractor import StateExtractor
from ..models import GameSnapshot
from ..parser import ClausewitzTextParser
from ..pause_controller import PauseController, PauseEvent
from ..save_unzipper import SaveFormatError, SaveUnzipper
from ..watcher import FileWatcher, SaveEvent, SaveEventType
from .advisor_panel import AdvisorPanel
from .dashboard_panel import DashboardPanel
from .log_panel import LogPanel
from .theme import DARK_STYLESHEET

logger = logging.getLogger(__name__)

# ── Worker thread: legge il save e produce un GameSnapshot ────────────────────

class _SaveWorker(QThread):
    """Thread separato per parsing e extraction — non blocca la UI."""

    snapshot_ready = pyqtSignal(object)  # GameSnapshot
    error          = pyqtSignal(str)

    def __init__(self, save_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._save_path = save_path
        self._unzipper  = SaveUnzipper()
        self._parser    = ClausewitzTextParser()
        self._extractor = StateExtractor()

    def run(self) -> None:
        try:
            text = self._unzipper.extract_gamestate(self._save_path)
            tree = self._parser.parse_text(text)
            snap = self._extractor.extract(tree)
            self.snapshot_ready.emit(snap)
        except SaveFormatError as exc:
            self.error.emit(f"Errore lettura save: {exc}")
        except Exception as exc:  # pragma: no cover
            self.error.emit(f"Errore inatteso: {exc}")
            logger.exception("SaveWorker: errore inatteso")


# ── MainWindow ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """Finestra principale EU4 Assistant sul secondo monitor.

    Gestisce l'intero ciclo: FileWatcher → SaveWorker → Panels aggiornati.
    """

    _SETTINGS_KEY = "eu4assistant/mainwindow"

    def __init__(
        self,
        save_path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._save_path  = save_path
        self._watcher: FileWatcher | None = None
        self._engine     = DecisionEngine()
        self._pause_ctrl = PauseController(on_pause=self._on_pause_event)
        self._settings   = QSettings("AronneZanichelli", "EU4Assistant")

        self._setup_window()
        self._setup_panels()
        self._restore_geometry()
        self._setup_hotkey()

    # ── Setup ──────────────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setWindowTitle("EU4 Assistant")
        self.setMinimumSize(QSize(900, 600))
        self.setStyleSheet(DARK_STYLESHEET)

        status = QStatusBar()
        self._status_label = QLabel("In attesa del save…")
        self._status_label.setStyleSheet("color: #6c7086; font-size: 12px;")
        status.addWidget(self._status_label)
        self.setStatusBar(status)

    def _setup_panels(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background-color: #313244; }")

        self._dashboard = DashboardPanel()
        self._advisor   = AdvisorPanel()
        self._log       = LogPanel()

        splitter.addWidget(self._dashboard)
        splitter.addWidget(self._advisor)
        splitter.addWidget(self._log)
        splitter.setSizes([240, 440, 220])

        main_layout.addWidget(splitter)

    def _restore_geometry(self) -> None:
        geom = self._settings.value(f"{self._SETTINGS_KEY}/geometry")
        if geom:
            self.restoreGeometry(geom)

    def _setup_hotkey(self) -> None:
        """Registra F2 per mostra/nascondi finestra (lazy import — solo su Windows)."""
        try:
            import keyboard
            keyboard.add_hotkey("f2", self._toggle_visibility)
            self._log.append("action", "Hotkey F2 registrata (mostra/nascondi)")
        except Exception as exc:
            logger.warning("Hotkey F2 non disponibile: %s", exc)
            self._log.append("error", f"Hotkey F2 non disponibile: {exc}")

    # ── Watcher public API ────────────────────────────────────────────────────

    def start_watching(self, save_path: Path) -> None:
        """Avvia il FileWatcher sul path del save."""
        self._save_path = save_path
        self._watcher = FileWatcher(save_path)
        self._watcher.start()
        self._log.append("action", f"Watching: {save_path}")
        self._status_label.setText(f"Watching: {save_path.name}")
        # Poll watcher queue ogni 500ms via QTimer
        from PyQt6.QtCore import QTimer
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self._poll_watcher)
        self._poll_timer.start()

    def stop_watching(self) -> None:
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
        if hasattr(self, "_poll_timer"):
            self._poll_timer.stop()

    # ── Slots ─────────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _poll_watcher(self) -> None:
        if not self._watcher:
            return
        event: SaveEvent | None = self._watcher.get(timeout=0)
        if event is None:
            return
        if event.type == SaveEventType.SAVE_CHANGED and event.path:
            self._status_label.setText("Parsing save…")
            worker = _SaveWorker(event.path, parent=self)
            worker.snapshot_ready.connect(self._on_snapshot_ready)
            worker.error.connect(self._on_worker_error)
            worker.start()
        elif event.type == SaveEventType.GAME_PAUSED:
            self._advisor.show_pause_banner("EU4 in pausa")
            self._log.append("alert", "EU4 in pausa — nessun autosave ricevuto")

    @pyqtSlot(object)
    def _on_snapshot_ready(self, snap: GameSnapshot) -> None:
        self._advisor.hide_pause_banner()
        self._dashboard.update_snapshot(snap)

        risks = self._engine.evaluate_risks(snap)
        recs  = self._engine.recommend(snap)
        self._advisor.update_recommendations(recs)
        self._advisor.update_alerts(risks)

        self._pause_ctrl.update(snap)
        self._status_label.setText(f"Aggiornato: {snap.eu4_date or snap.timestamp[:10]}")
        self._log.append("decision", f"Snapshot aggiornato — {len(recs)} raccomandazioni")

    @pyqtSlot(str)
    def _on_worker_error(self, msg: str) -> None:
        self._status_label.setText("Errore parsing")
        self._log.append("error", msg)

    def _on_pause_event(self, event: PauseEvent) -> None:
        self._advisor.show_pause_banner(event.detail)
        self._log.append("alert", f"Pausa automatica: {event.detail}")

    # ── Visibilità ────────────────────────────────────────────────────────────

    def _toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._settings.setValue(f"{self._SETTINGS_KEY}/geometry", self.saveGeometry())
        self.stop_watching()
        super().closeEvent(event)
