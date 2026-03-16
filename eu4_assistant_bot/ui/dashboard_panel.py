"""Dashboard panel — left column showing live game state."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from ..models import GameSnapshot


class DashboardPanel(QWidget):
    """Left panel: country tag, date, economy bars, military stats."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── Header: country + date ──
        self._lbl_country = QLabel("---")
        self._lbl_country.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self._lbl_country)

        self._lbl_date = QLabel("")
        self._lbl_date.setStyleSheet("font-size: 13px; color: #aaa;")
        layout.addWidget(self._lbl_date)

        layout.addWidget(self._separator())

        # ── Economy bars ──
        layout.addWidget(QLabel("Treasury"))
        self._bar_treasury = self._make_bar(0, 10000)
        layout.addWidget(self._bar_treasury)

        self._lbl_income_expenses = QLabel("Income: 0 | Expenses: 0 | Debt: 0")
        self._lbl_income_expenses.setStyleSheet("font-size: 11px; color: #bbb;")
        layout.addWidget(self._lbl_income_expenses)

        layout.addWidget(self._separator())

        # ── Military ──
        layout.addWidget(QLabel("Manpower"))
        self._bar_manpower = self._make_bar(0, 100000)
        layout.addWidget(self._bar_manpower)

        self._lbl_force_limit = QLabel("Force limit: 0")
        self._lbl_force_limit.setStyleSheet("font-size: 11px; color: #bbb;")
        layout.addWidget(self._lbl_force_limit)

        layout.addWidget(self._separator())

        # ── Stability / Prestige / Legitimacy ──
        self._lbl_stability = QLabel("Stability: 0")
        layout.addWidget(self._lbl_stability)
        self._lbl_prestige = QLabel("Prestige: 0.0")
        layout.addWidget(self._lbl_prestige)
        self._lbl_legitimacy = QLabel("Legitimacy: 100.0")
        layout.addWidget(self._lbl_legitimacy)

        layout.addStretch()

    # ── Public API ──────────────────────────────────────────────────────────

    def update_snapshot(self, snap: GameSnapshot) -> None:
        self._lbl_country.setText(snap.country)
        self._lbl_date.setText(snap.eu4_date or "---")

        self._bar_treasury.setMaximum(max(int(snap.economy.treasury * 2), 1))
        self._bar_treasury.setValue(int(snap.economy.treasury))
        self._lbl_income_expenses.setText(
            f"Income: {snap.economy.income:.1f} | "
            f"Expenses: {snap.economy.expenses:.1f} | "
            f"Debt: {snap.economy.debt:.0f}"
        )

        self._bar_manpower.setMaximum(max(snap.military.force_limit * 1000, 1))
        self._bar_manpower.setValue(snap.military.manpower)
        self._lbl_force_limit.setText(f"Force limit: {snap.military.force_limit}")

        self._lbl_stability.setText(f"Stability: {snap.stability:+d}")
        self._lbl_prestige.setText(f"Prestige: {snap.prestige:.1f}")
        self._lbl_legitimacy.setText(f"Legitimacy: {snap.legitimacy:.1f}")

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _make_bar(minimum: int, maximum: int) -> QProgressBar:
        bar = QProgressBar()
        bar.setMinimum(minimum)
        bar.setMaximum(maximum)
        bar.setValue(0)
        bar.setTextVisible(True)
        return bar

    @staticmethod
    def _separator() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #444;")
        return line
