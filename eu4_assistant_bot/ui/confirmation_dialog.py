"""Confirmation dialog for semi-bot mode — shown before executing actions."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..models import ActionPlan


class ConfirmationDialog(QDialog):
    """Modal dialog showing action details before execution."""

    def __init__(self, plan: ActionPlan, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Conferma azione")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setStyleSheet(
            "QDialog { background: #1e1e1e; color: #ddd; }"
        )

        self._confirmed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        # Action type
        lbl_action = QLabel(plan.action_type.replace("_", " ").title())
        lbl_action.setStyleSheet("font-weight: bold; font-size: 16px; color: #4a9;")
        layout.addWidget(lbl_action)

        layout.addSpacing(8)

        # Details
        details = [
            ("Priorità", f"{plan.priority:.0%}"),
            ("Confidenza", f"{plan.confidence:.0%}"),
        ]
        target = plan.expected_outcome.get("target_metric", "")
        if target:
            details.append(("Obiettivo", str(target)))
        current = plan.expected_outcome.get("current_value", "")
        if current != "":
            details.append(("Valore attuale", str(current)))

        for label, value in details:
            row = QHBoxLayout()
            lbl_k = QLabel(f"{label}:")
            lbl_k.setStyleSheet("font-size: 12px; color: #888;")
            lbl_v = QLabel(value)
            lbl_v.setStyleSheet("font-size: 12px; color: #ddd;")
            row.addWidget(lbl_k)
            row.addStretch()
            row.addWidget(lbl_v)
            layout.addLayout(row)

        if plan.requires_confirmation:
            lbl_warn = QLabel("Questa azione richiede conferma esplicita.")
            lbl_warn.setStyleSheet("font-size: 11px; color: #f90; margin-top: 8px;")
            layout.addWidget(lbl_warn)

        layout.addSpacing(16)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Annulla")
        btn_cancel.setFixedWidth(100)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton("Conferma")
        btn_confirm.setFixedWidth(100)
        btn_confirm.setStyleSheet(
            "QPushButton { background: #4a9; color: #111; font-weight: bold; }"
        )
        btn_confirm.clicked.connect(self._on_confirm)
        btn_row.addWidget(btn_confirm)

        layout.addLayout(btn_row)

    def _on_confirm(self) -> None:
        self._confirmed = True
        self.accept()

    def was_confirmed(self) -> bool:
        return self._confirmed
