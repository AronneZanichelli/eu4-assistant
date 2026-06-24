"""Advisor panel — center column with top-3 recommendations and alert badges."""
from __future__ import annotations

from enum import Enum

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config import BotMode
from ..decision_engine import Recommendation, RiskAlerts
from .bot_params_panel import BotParamsPanel


class BotState(Enum):
    """Visible full-bot state (design §5.5)."""
    OFF = "off"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


# icon + label + colour per state, single source of truth for the indicator.
_BOT_STATE_DISPLAY: dict[BotState, tuple[str, str]] = {
    BotState.OFF: ("○ Off", "#777"),
    BotState.ACTIVE: ("● Attivo", "#4a9"),
    BotState.PAUSED: ("⏸ In pausa", "#fc0"),
    BotState.ERROR: ("✕ Errore", "#b22"),
}


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
    mode_changed = pyqtSignal(object)    # BotMode chosen by the user via the mode selector

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

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

        # ── Full-bot parameters panel ──
        self.bot_params = BotParamsPanel()
        layout.addWidget(self.bot_params)

        # ── Mode switch ──
        mode_row = QHBoxLayout()
        self._lbl_mode = QLabel("Modalità: Advisor")
        self._lbl_mode.setStyleSheet("font-size: 12px; color: #aaa;")
        mode_row.addWidget(self._lbl_mode)
        mode_row.addStretch()
        self._bot_state = BotState.OFF
        self._lbl_bot_state = QLabel()
        mode_row.addWidget(self._lbl_bot_state)
        self.set_bot_state(BotState.OFF)
        self._mode_combo = QComboBox()
        for mode in (BotMode.ASSIST, BotMode.SEMI_BOT, BotMode.FULL_BOT):
            self._mode_combo.addItem(mode.display_label, mode)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_combo_changed)
        mode_row.addWidget(self._mode_combo)
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

    def set_bot_state(self, state: BotState) -> None:
        """Update the visible full-bot state indicator (design §5.5)."""
        self._bot_state = state
        text, colour = _BOT_STATE_DISPLAY[state]
        self._lbl_bot_state.setText(text)
        self._lbl_bot_state.setStyleSheet(
            f"font-size: 12px; font-weight: bold; color: {colour};"
        )

    def select_mode(self, mode: BotMode) -> None:
        """Sync the mode selector programmatically without emitting mode_changed."""
        idx = self._mode_combo.findData(mode)
        if idx >= 0:
            self._mode_combo.blockSignals(True)
            self._mode_combo.setCurrentIndex(idx)
            self._mode_combo.blockSignals(False)
        self.set_mode_label(mode.display_label)

    def _on_mode_combo_changed(self) -> None:
        mode = self._mode_combo.currentData()
        if mode is not None:
            self.set_mode_label(mode.display_label)
            self.mode_changed.emit(mode)

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
