"""Log panel — right column with chronological event feed."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LogLevel(str, Enum):
    DECISION = "decision"
    ACTION = "action"
    ALERT = "alert"
    ERROR = "error"


_LEVEL_COLORS: dict[LogLevel, str] = {
    LogLevel.DECISION: "#4a9",
    LogLevel.ACTION: "#49f",
    LogLevel.ALERT: "#f90",
    LogLevel.ERROR: "#e44",
}


class LogPanel(QWidget):
    """Right panel: chronological event feed with filters and CSV export."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── Filter buttons ──
        filter_row = QHBoxLayout()
        self._filters: dict[LogLevel, QPushButton] = {}
        for level in LogLevel:
            btn = QPushButton(level.value.capitalize())
            btn.setCheckable(True)
            btn.setChecked(True)
            btn.setFixedWidth(72)
            btn.clicked.connect(self._apply_filters)
            self._filters[level] = btn
            filter_row.addWidget(btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        # ── Event list ──
        self._list = QListWidget()
        self._list.setStyleSheet("font-size: 11px;")
        layout.addWidget(self._list)

        # ── Export button ──
        self._btn_export = QPushButton("Export CSV")
        self._btn_export.setFixedWidth(100)
        self._btn_export.clicked.connect(self._export_csv)
        layout.addWidget(self._btn_export, alignment=Qt.AlignmentFlag.AlignRight)

        # Internal storage for filtering
        self._entries: list[tuple[str, LogLevel, str]] = []  # (timestamp, level, message)

    # ── Public API ──────────────────────────────────────────────────────────

    def add_entry(self, level: LogLevel, message: str) -> None:
        ts = datetime.now(tz=timezone.utc).strftime("%H:%M:%S")
        self._entries.append((ts, level, message))
        self._add_item(ts, level, message)

    # ── Internal ───────────────────────────────────────────────────────────

    def _add_item(self, ts: str, level: LogLevel, message: str) -> None:
        if not self._filters[level].isChecked():
            return
        color = _LEVEL_COLORS[level]
        item = QListWidgetItem(f"[{ts}] [{level.value.upper()}] {message}")
        item.setForeground(Qt.GlobalColor.white)
        item.setData(Qt.ItemDataRole.UserRole, level.value)
        self._list.addItem(item)
        self._list.scrollToBottom()

    def _apply_filters(self) -> None:
        self._list.clear()
        for ts, level, msg in self._entries:
            self._add_item(ts, level, msg)

    def _export_csv(self) -> None:
        out = Path.home() / ".eu4-assistant" / "session_log.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["timestamp", "level", "message"])
        for ts, level, msg in self._entries:
            writer.writerow([ts, level.value, msg])
        out.write_text(buf.getvalue(), encoding="utf-8")
