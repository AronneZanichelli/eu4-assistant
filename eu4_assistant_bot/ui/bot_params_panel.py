"""Full-bot parameters panel — budget, limits, categories, colonial mode and
configurable alert thresholds (design §8.8 / §5.3).

Bound to :class:`BotParams`; round-trips via ``set_params`` / ``get_params`` so
the values can be persisted to ``bot_params.json`` between sessions. The active
mode is owned by the top-level mode switch, so ``get_params`` takes it as an
argument rather than storing it here.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..config import _DEFAULT_CATEGORIES, BotMode, BotParams, RiskProfile


class BotParamsPanel(QWidget):
    """Editor for the persisted full-bot parameters."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        box = QGroupBox("Parametri full-bot")
        form = QFormLayout(box)

        self._spend = QDoubleSpinBox()
        self._spend.setRange(0.0, 1.0)
        self._spend.setSingleStep(0.05)
        self._spend.setDecimals(2)
        form.addRow("Budget (quota spesa mensile)", self._spend)

        self._recruits = QSpinBox()
        self._recruits.setRange(0, 99)
        form.addRow("Limite reclute / ciclo", self._recruits)

        self._risk = QComboBox()
        for profile in (RiskProfile.SAFE, RiskProfile.BALANCED, RiskProfile.AGGRESSIVE):
            self._risk.addItem(profile.value, profile)
        form.addRow("Profilo rischio", self._risk)

        self._colonial = QComboBox()
        self._colonial.addItem("Autonomo", "autonomous")
        self._colonial.addItem("Lista target", "target_list")
        form.addRow("Modalità colonial", self._colonial)

        self._targets = QLineEdit()
        self._targets.setPlaceholderText("es. 484, 482")
        form.addRow("Province target (id, separati da virgola)", self._targets)

        # Enabled categories — one checkbox per actionable category.
        cats_row = QHBoxLayout()
        self._categories: dict[str, QCheckBox] = {}
        for cat in _DEFAULT_CATEGORIES:
            cb = QCheckBox(cat)
            self._categories[cat] = cb
            cats_row.addWidget(cb)
        form.addRow("Categorie abilitate", _wrap(cats_row))

        # Configurable alert thresholds (only coalition / manpower; design §8.8).
        self._coalition = QDoubleSpinBox()
        self._coalition.setRange(0.0, 1.0)
        self._coalition.setSingleStep(0.05)
        self._coalition.setDecimals(2)
        form.addRow("Soglia coalition", self._coalition)

        self._manpower = QDoubleSpinBox()
        self._manpower.setRange(0.0, 1.0)
        self._manpower.setSingleStep(0.05)
        self._manpower.setDecimals(2)
        form.addRow("Soglia manpower", self._manpower)

        outer.addWidget(box)

        self.set_params(BotParams())

    def set_params(self, bp: BotParams) -> None:
        self._spend.setValue(bp.max_monthly_spend_ratio)
        self._recruits.setValue(bp.max_recruits_per_cycle)
        self._risk.setCurrentIndex(self._risk.findData(bp.risk_profile))
        self._colonial.setCurrentIndex(self._colonial.findData(bp.colonial_mode))
        self._targets.setText(", ".join(str(x) for x in bp.colonial_targets))
        for cat, cb in self._categories.items():
            cb.setChecked(cat in bp.enabled_categories)
        self._coalition.setValue(bp.coalition_risk_threshold)
        self._manpower.setValue(bp.manpower_ratio_threshold)

    def get_params(self, mode: BotMode) -> BotParams:
        targets: list[int] = []
        for tok in self._targets.text().split(","):
            tok = tok.strip()
            if tok:
                try:
                    targets.append(int(tok))
                except ValueError:
                    pass  # silently ignore non-numeric tokens
        return BotParams(
            mode=mode,
            risk_profile=self._risk.currentData(),
            max_monthly_spend_ratio=self._spend.value(),
            max_recruits_per_cycle=self._recruits.value(),
            enabled_categories=[c for c in _DEFAULT_CATEGORIES if self._categories[c].isChecked()],
            colonial_mode=self._colonial.currentData(),
            colonial_targets=targets,
            coalition_risk_threshold=self._coalition.value(),
            manpower_ratio_threshold=self._manpower.value(),
        )


def _wrap(layout: QHBoxLayout) -> QWidget:
    """Wrap a layout in a QWidget so it can be added as a QFormLayout row field."""
    w = QWidget()
    layout.setContentsMargins(0, 0, 0, 0)
    w.setLayout(layout)
    return w
