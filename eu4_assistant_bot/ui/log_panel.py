from __future__ import annotations

import csv
import io
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget, QFileDialog,
)


class LogPanel(QWidget):
    """Colonna destra: feed eventi cronologico, filtro, export CSV."""

    _CATEGORIES = ["Tutti", "Decision", "Action", "Alert", "Error"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entries: list[dict] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Header + filtro ───────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("LOG EVENTI")
        title.setObjectName("section_title")
        self._filter = QComboBox()
        self._filter.addItems(self._CATEGORIES)
        self._filter.currentTextChanged.connect(self._apply_filter)
        self._filter.setFixedWidth(100)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self._filter)
        layout.addLayout(header)

        # ── Feed ──────────────────────────────────────────────────────────────
        frame = QFrame()
        frame.setObjectName("panel")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(4, 4, 4, 4)
        self._feed = QPlainTextEdit()
        self._feed.setObjectName("log_feed")
        self._feed.setReadOnly(True)
        self._feed.setMaximumBlockCount(500)
        frame_layout.addWidget(self._feed)
        layout.addWidget(frame, 1)

        # ── Export ────────────────────────────────────────────────────────────
        export_btn = QPushButton("Esporta CSV")
        export_btn.setObjectName("mode_btn")
        export_btn.clicked.connect(self._export_csv)
        layout.addWidget(export_btn)

    def append(self, category: str, message: str) -> None:
        """Aggiunge un evento al feed."""
        ts = datetime.now().strftime("%H:%M:%S")
        entry = {"ts": ts, "category": category, "message": message}
        self._entries.append(entry)

        active_filter = self._filter.currentText()
        if active_filter == "Tutti" or active_filter.lower() == category.lower():
            self._feed.appendPlainText(f"[{ts}] [{category.upper():8}] {message}")
            # Scroll to bottom
            sb = self._feed.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _apply_filter(self, category: str) -> None:
        self._feed.clear()
        for entry in self._entries:
            if category == "Tutti" or category.lower() == entry["category"].lower():
                self._feed.appendPlainText(
                    f"[{entry['ts']}] [{entry['category'].upper():8}] {entry['message']}"
                )

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Esporta log", "eu4_session_log.csv", "CSV (*.csv)"
        )
        if not path:
            return
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["ts", "category", "message"])
        writer.writeheader()
        writer.writerows(self._entries)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(buf.getvalue())
        self.append("action", f"Log esportato: {path}")
