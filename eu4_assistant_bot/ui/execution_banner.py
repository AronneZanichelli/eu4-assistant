"""Execution banner — live action display at top of Advisor panel."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class ExecutionBanner(QFrame):
    """Banner shown at top of AdvisorPanel during action execution."""

    undo_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { background: #2a3a2a; border: 1px solid #4a9; border-radius: 6px; padding: 6px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        top_row = QHBoxLayout()
        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet("font-weight: bold; font-size: 13px; color: #6c6;")
        top_row.addWidget(self._lbl_status)
        top_row.addStretch()

        self._btn_stop = QPushButton("STOP")
        self._btn_stop.setFixedWidth(60)
        self._btn_stop.setStyleSheet(
            "QPushButton { background: #b22; color: white; font-weight: bold; border-radius: 4px; }"
        )
        self._btn_stop.clicked.connect(self.stop_requested.emit)
        top_row.addWidget(self._btn_stop)

        self._btn_undo = QPushButton("Annulla ultima")
        self._btn_undo.setFixedWidth(110)
        self._btn_undo.setStyleSheet(
            "QPushButton { background: #c80; color: white; font-weight: bold; border-radius: 4px; }"
        )
        self._btn_undo.clicked.connect(self.undo_requested.emit)
        self._btn_undo.setVisible(False)
        top_row.addWidget(self._btn_undo)

        layout.addLayout(top_row)

        self._lbl_detail = QLabel("")
        self._lbl_detail.setStyleSheet("font-size: 11px; color: #aaa;")
        self._lbl_detail.setWordWrap(True)
        layout.addWidget(self._lbl_detail)

        self.setVisible(False)

    def show_executing(self, description: str) -> None:
        self._lbl_status.setText(f"Sto eseguendo: {description}")
        self._lbl_status.setStyleSheet("font-weight: bold; font-size: 13px; color: #6c6;")
        self._lbl_detail.setText("")
        self._btn_stop.setVisible(True)
        self._btn_undo.setVisible(False)
        self.setStyleSheet(
            "QFrame { background: #2a3a2a; border: 1px solid #4a9; border-radius: 6px; padding: 6px; }"
        )
        self.setVisible(True)

    def show_eu4_paused(self) -> None:
        self._lbl_status.setText("EU4 in pausa — bot in attesa")
        self._lbl_status.setStyleSheet("font-weight: bold; font-size: 13px; color: #cc0;")
        self._lbl_detail.setText("Il bot riprenderà automaticamente al primo nuovo autosave.")
        self._btn_stop.setVisible(False)
        self._btn_undo.setVisible(False)
        self.setStyleSheet(
            "QFrame { background: #3a3a2a; border: 1px solid #cc0; border-radius: 6px; padding: 6px; }"
        )
        self.setVisible(True)

    def show_undo_available(self, description: str) -> None:
        self._lbl_status.setText(f"Completato: {description}")
        self._lbl_status.setStyleSheet("font-weight: bold; font-size: 13px; color: #6c6;")
        self._lbl_detail.setText("Azione critica — puoi annullare.")
        self._btn_stop.setVisible(False)
        self._btn_undo.setVisible(True)
        self.setVisible(True)

    def hide_banner(self) -> None:
        self.setVisible(False)
        self._btn_undo.setVisible(False)
