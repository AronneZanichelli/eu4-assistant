from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from ..decision_engine import Recommendation, RiskAlerts
from ..models import GameSnapshot


class RecommendationCard(QFrame):
    """Card singola per una raccomandazione dell'Advisor."""

    execute_requested = pyqtSignal(str)  # emette recommendation title

    def __init__(self, rec: Recommendation, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rec_card")
        self._rec = rec
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Riga titolo + categoria
        top = QHBoxLayout()
        title = QLabel(self._rec.title)
        title.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        cat = QLabel(self._rec.category.upper())
        cat.setStyleSheet("color: #89b4fa; font-size: 11px;")
        cat.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(title, 1)
        top.addWidget(cat)
        layout.addLayout(top)

        # Testo rationale
        rationale = QLabel(self._rec.rationale)
        rationale.setStyleSheet("color: #a6adc8; font-size: 12px;")
        rationale.setWordWrap(True)
        layout.addWidget(rationale)

        # Score + pulsante Esegui
        bottom = QHBoxLayout()
        score_lbl = QLabel(f"Priorità: {self._rec.priority:.0%}")
        score_lbl.setStyleSheet("color: #6c7086; font-size: 11px;")
        btn = QPushButton("Esegui")
        btn.setObjectName("execute_btn")
        btn.setEnabled(False)  # abilitato in M8
        btn.setToolTip("Disponibile in M8 con ActionExecutor")
        btn.clicked.connect(lambda: self.execute_requested.emit(self._rec.title))
        bottom.addWidget(score_lbl)
        bottom.addStretch()
        bottom.addWidget(btn)
        layout.addLayout(bottom)


class AdvisorPanel(QWidget):
    """Colonna centrale: top-3 recommendation cards, badge alert, switch modalità."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ── Switch modalità ───────────────────────────────────────────────────
        mode_frame = QFrame()
        mode_frame.setObjectName("panel")
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(10, 6, 10, 6)

        mode_lbl = QLabel("MODALITÀ")
        mode_lbl.setObjectName("section_title")
        self._advisor_btn = QPushButton("Advisor")
        self._advisor_btn.setObjectName("mode_btn")
        self._advisor_btn.setCheckable(True)
        self._advisor_btn.setChecked(True)
        self._fullbot_btn = QPushButton("⏸ Full-bot")
        self._fullbot_btn.setObjectName("mode_btn")
        self._fullbot_btn.setCheckable(True)
        self._fullbot_btn.setToolTip("Disponibile in M8")
        self._fullbot_btn.setEnabled(False)

        self._bot_status = QLabel("● Off")
        self._bot_status.setStyleSheet("color: #6c7086; font-size: 12px;")

        mode_layout.addWidget(mode_lbl)
        mode_layout.addStretch()
        mode_layout.addWidget(self._advisor_btn)
        mode_layout.addWidget(self._fullbot_btn)
        mode_layout.addWidget(self._bot_status)
        layout.addWidget(mode_frame)

        # ── Badge alert ───────────────────────────────────────────────────────
        self._alert_bar = QFrame()
        self._alert_bar.setObjectName("panel")
        self._alert_layout = QHBoxLayout(self._alert_bar)
        self._alert_layout.setContentsMargins(10, 4, 10, 4)
        self._alert_layout.setSpacing(6)
        self._alert_lbl = QLabel("Nessun alert attivo")
        self._alert_lbl.setStyleSheet("color: #6c7086; font-size: 12px;")
        self._alert_layout.addWidget(self._alert_lbl)
        self._alert_layout.addStretch()
        layout.addWidget(self._alert_bar)

        # ── Recommendation cards ──────────────────────────────────────────────
        rec_label = QLabel("TOP RACCOMANDAZIONI")
        rec_label.setObjectName("section_title")
        layout.addWidget(rec_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(6)
        self._cards_layout.addStretch()
        scroll.setWidget(self._cards_container)
        layout.addWidget(scroll, 1)

        # ── Pausa banner ──────────────────────────────────────────────────────
        self._pause_banner = QLabel("")
        self._pause_banner.setStyleSheet(
            "background-color: #f38ba8; color: #1e1e2e; border-radius: 4px;"
            " padding: 6px; font-weight: bold;"
        )
        self._pause_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pause_banner.hide()
        layout.addWidget(self._pause_banner)

    def update_recommendations(self, recs: list[Recommendation]) -> None:
        """Sostituisce le cards con le nuove top-3 raccomandazioni."""
        # Rimuovi cards esistenti (non lo stretch)
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for rec in recs[:3]:
            card = RecommendationCard(rec)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

        if not recs:
            placeholder = QLabel("Nessuna raccomandazione attiva.")
            placeholder.setStyleSheet("color: #6c7086; font-style: italic; padding: 12px;")
            self._cards_layout.insertWidget(0, placeholder)

    def update_alerts(self, risks: RiskAlerts) -> None:
        """Aggiorna i badge alert."""
        # Rimuovi badge esistenti
        while self._alert_layout.count() > 1:
            item = self._alert_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        active = []
        if risks.coalition_risk: active.append(("⚠ Coalizione", "alert_badge"))
        if risks.debt_risk:      active.append(("💸 Debito",     "alert_badge_warn"))
        if risks.manpower_risk:  active.append(("⚔ Manpower",   "alert_badge_warn"))
        if risks.rebels_risk:    active.append(("🔥 Ribelli",    "alert_badge"))

        if active:
            self._alert_lbl.hide()
            for text, obj_name in active:
                badge = QLabel(text)
                badge.setObjectName(obj_name)
                self._alert_layout.insertWidget(self._alert_layout.count() - 1, badge)
        else:
            self._alert_lbl.show()
            self._alert_lbl.setText("Nessun alert attivo")

    def show_pause_banner(self, message: str) -> None:
        self._pause_banner.setText(f"⏸ PAUSA AUTOMATICA — {message}")
        self._pause_banner.show()

    def hide_pause_banner(self) -> None:
        self._pause_banner.hide()
