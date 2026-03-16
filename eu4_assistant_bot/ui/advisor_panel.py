"""Advisor panel — center column with top-3 recommendations and alert badges."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..decision_engine import Recommendation, RiskAlerts
from .execution_banner import ExecutionBanner


class _RecommendationCard(QFrame):
    """Single recommendation card with title, rationale, score, and [Esegui] button."""

    execute_clicked = pyqtSignal(str)  # emits category

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { border: 1px solid #555; border-radius: 6px; padding: 8px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        top_row = QHBoxLayout()
        self._lbl_title = QLabel("—")
        self._lbl_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        top_row.addWidget(self._lbl_title)
        top_row.addStretch()
        self._lbl_score = QLabel("")
        self._lbl_score.setStyleSheet("font-size: 11px; color: #f90;")
        top_row.addWidget(self._lbl_score)
        layout.addLayout(top_row)

        self._lbl_category = QLabel("")
        self._lbl_category.setStyleSheet("font-size: 10px; color: #888;")
        layout.addWidget(self._lbl_category)

        self._lbl_rationale = QLabel("")
        self._lbl_rationale.setWordWrap(True)
        self._lbl_rationale.setStyleSheet("font-size: 11px; color: #ccc;")
        layout.addWidget(self._lbl_rationale)

        self._btn_execute = QPushButton("Esegui")
        self._btn_execute.setFixedWidth(80)
        self._btn_execute.clicked.connect(self._on_execute)
        layout.addWidget(self._btn_execute, alignment=Qt.AlignmentFlag.AlignRight)

        self._category = ""

    def set_recommendation(self, rec: Recommendation) -> None:
        self._lbl_title.setText(rec.title)
        self._lbl_score.setText(f"{rec.priority:.0%}")
        self._lbl_category.setText(rec.category.upper())
        self._lbl_rationale.setText(rec.rationale)
        self._category = rec.category

    def _on_execute(self) -> None:
        self.execute_clicked.emit(self._category)


class AdvisorPanel(QWidget):
    """Center panel: top-3 recommendation cards + alert badges + mode switch."""

    execute_requested = pyqtSignal(str)  # category of the recommendation to execute

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── Execution banner (hidden by default) ──
        self._execution_banner = ExecutionBanner()
        self._execution_banner.stop_requested.connect(lambda: self.execute_requested.emit("__stop__"))
        layout.addWidget(self._execution_banner)

        # ── Alert badges row ──
        self._alert_row = QHBoxLayout()
        self._alert_labels: dict[str, QLabel] = {}
        for tag in ("AE", "Coalition", "Debt", "Manpower", "Rebels", "War"):
            lbl = QLabel(tag)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedWidth(72)
            lbl.setStyleSheet(
                "background: #333; color: #777; border-radius: 4px; padding: 2px 6px; font-size: 11px;"
            )
            self._alert_row.addWidget(lbl)
            self._alert_labels[tag.lower()] = lbl
        self._alert_row.addStretch()
        layout.addLayout(self._alert_row)

        layout.addSpacing(8)

        # ── Recommendation cards ──
        self._cards: list[_RecommendationCard] = []
        for _ in range(3):
            card = _RecommendationCard()
            card.execute_clicked.connect(self.execute_requested.emit)
            self._cards.append(card)
            layout.addWidget(card)

        layout.addStretch()

        # ── Mode switch ──
        mode_row = QHBoxLayout()
        self._lbl_mode = QLabel("Modalità: Advisor")
        self._lbl_mode.setStyleSheet("font-size: 12px; color: #aaa;")
        mode_row.addWidget(self._lbl_mode)
        mode_row.addStretch()
        layout.addLayout(mode_row)

    # ── Public API ──────────────────────────────────────────────────────────

    def update_recommendations(self, recs: list[Recommendation]) -> None:
        for i, card in enumerate(self._cards):
            if i < len(recs):
                card.set_recommendation(recs[i])
                card.setVisible(True)
            else:
                card.setVisible(False)

    def update_alerts(self, alerts: RiskAlerts) -> None:
        self._set_badge("coalition", alerts.coalition_risk)
        self._set_badge("debt", alerts.debt_risk)
        self._set_badge("manpower", alerts.manpower_risk)
        self._set_badge("rebels", alerts.rebels_risk)

    def set_mode_label(self, text: str) -> None:
        self._lbl_mode.setText(f"Modalità: {text}")

    # ── Execution banner API ──────────────────────────────────────────────

    def show_execution_banner(self, description: str) -> None:
        self._execution_banner.show_executing(description)

    def hide_execution_banner(self) -> None:
        self._execution_banner.hide_banner()

    def show_eu4_paused(self) -> None:
        self._execution_banner.show_eu4_paused()

    def show_undo_available(self, description: str) -> None:
        self._execution_banner.show_undo_available(description)

    @property
    def execution_banner(self) -> ExecutionBanner:
        return self._execution_banner

    def _set_badge(self, key: str, active: bool) -> None:
        lbl = self._alert_labels.get(key)
        if lbl is None:
            return
        if active:
            lbl.setStyleSheet(
                "background: #b22; color: #fff; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: bold;"
            )
        else:
            lbl.setStyleSheet(
                "background: #333; color: #777; border-radius: 4px; padding: 2px 6px; font-size: 11px;"
            )
