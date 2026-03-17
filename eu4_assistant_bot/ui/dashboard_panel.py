from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget,
)

from ..models import GameSnapshot


class DashboardPanel(QWidget):
    """Colonna sinistra: bandiera, data, barre economia, militare, stabilità."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # ── Header: tag + data ────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("panel")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(10, 8, 10, 8)

        self._tag_label = QLabel("—")
        self._tag_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #89b4fa;")
        self._tag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._date_label = QLabel("—")
        self._date_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self._date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        h_layout.addWidget(self._tag_label)
        h_layout.addWidget(self._date_label)
        layout.addWidget(header)

        # ── Economia ──────────────────────────────────────────────────────────
        eco_frame = self._section("ECONOMIA")
        eco_layout = eco_frame.layout()
        self._treasury_bar  = self._bar("treasury",  "Tesoro",    "#a6e3a1", eco_layout)
        self._income_bar    = self._bar("income",    "Entrate",   "#89b4fa", eco_layout)
        self._expenses_bar  = self._bar("expenses",  "Uscite",    "#f38ba8", eco_layout)
        self._debt_bar      = self._bar("debt",      "Debito",    "#fab387", eco_layout)
        layout.addWidget(eco_frame)

        # ── Militare ──────────────────────────────────────────────────────────
        mil_frame = self._section("MILITARE")
        mil_layout = mil_frame.layout()
        self._manpower_bar  = self._bar("manpower", "Manpower",  "#cba6f7", mil_layout)
        self._fl_label      = QLabel("Force limit: —")
        self._fl_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        mil_layout.addWidget(self._fl_label)
        layout.addWidget(mil_frame)

        # ── Stabilità / Prestigio / Legittimità ──────────────────────────────
        stat_frame = self._section("STATO")
        stat_layout = stat_frame.layout()
        self._stability_label  = self._stat_row("Stabilità",   stat_layout)
        self._prestige_label   = self._stat_row("Prestigio",   stat_layout)
        self._legitimacy_label = self._stat_row("Legittimità", stat_layout)
        layout.addWidget(stat_frame)

        layout.addStretch()

    def update_snapshot(self, snap: GameSnapshot) -> None:
        """Aggiorna tutti i widget con i dati del nuovo snapshot."""
        self._tag_label.setText(snap.country)
        self._date_label.setText(snap.eu4_date or snap.timestamp[:10])

        eco = snap.economy
        max_val = max(abs(eco.treasury), abs(eco.income), abs(eco.expenses), abs(eco.debt), 1)
        self._set_bar(self._treasury_bar, eco.treasury, max_val,  f"{eco.treasury:.0f} d")
        self._set_bar(self._income_bar,   eco.income,   max_val,  f"{eco.income:.1f}/m")
        self._set_bar(self._expenses_bar, eco.expenses, max_val,  f"{eco.expenses:.1f}/m")
        self._set_bar(self._debt_bar,     eco.debt,     max_val,  f"{eco.debt:.0f} d")

        mil = snap.military
        max_mp = max(mil.manpower, mil.force_limit * 1000, 1)
        self._set_bar(self._manpower_bar, mil.manpower, max_mp, f"{mil.manpower // 1000}K")
        self._fl_label.setText(f"Force limit: {mil.force_limit}")

        self._stability_label.setText(f"Stabilità: {snap.stability:+d}")
        self._prestige_label.setText(f"Prestigio: {snap.prestige:.0f}")
        self._legitimacy_label.setText(f"Legittimità: {snap.legitimacy:.0f}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _section(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        lbl = QLabel(title)
        lbl.setObjectName("section_title")
        layout.addWidget(lbl)
        return frame

    def _bar(self, name: str, label: str, color: str, parent_layout: QVBoxLayout) -> QProgressBar:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(60)
        lbl.setStyleSheet("color: #a6adc8; font-size: 12px;")
        bar = QProgressBar()
        bar.setObjectName(name)
        bar.setMaximum(1000)
        bar.setValue(0)
        bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}")
        bar.setTextVisible(False)
        self._bar_val_label = QLabel("—")
        row.addWidget(lbl)
        row.addWidget(bar, 1)
        parent_layout.addLayout(row)
        return bar

    @staticmethod
    def _set_bar(bar: QProgressBar, value: float, max_val: float, text: str) -> None:
        pct = int(min(abs(value) / max(abs(max_val), 1) * 1000, 1000))
        bar.setValue(pct)
        bar.setFormat(text)
        bar.setTextVisible(True)

    def _stat_row(self, label: str, parent_layout: QVBoxLayout) -> QLabel:
        lbl = QLabel(f"{label}: —")
        lbl.setStyleSheet("color: #cdd6f4; font-size: 12px;")
        parent_layout.addWidget(lbl)
        return lbl
