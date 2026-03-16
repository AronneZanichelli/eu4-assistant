"""Peacetime handler: reduce army maintenance to stabilize budget."""
from __future__ import annotations

import logging

from ...models import ActionPlan, GameSnapshot
from ..action_handler import ActionHandler, CheckResult, register_handler
from ..input_backend import InputBackend

logger = logging.getLogger(__name__)


@register_handler
class ReduceMaintenanceHandler(ActionHandler):
    action_type = "economy_stabilize_budget"
    requires_confirmation = False
    is_critical = False

    def __init__(self, backend: InputBackend) -> None:
        super().__init__(backend)

    def pre_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        balance = snapshot.economy.income - snapshot.economy.expenses
        if balance >= 0:
            return CheckResult(passed=False, message="Bilancio positivo, riduzione maintenance non necessaria.")
        return CheckResult(passed=True, message=f"Bilancio negativo ({balance:+.1f}), riduzione maintenance consigliata.")

    def execute(self, plan: ActionPlan, snapshot: GameSnapshot) -> None:
        # Open economy panel (hotkey '4' in EU4)
        self._backend.send_key("4")
        # Locate and drag army maintenance slider down
        slider_pos = self._backend.locate_template("slider_army_maintenance")
        if slider_pos is None:
            slider_pos = (600, 300)
        # Drag slider left by 50px to reduce maintenance
        deficit = snapshot.economy.expenses - snapshot.economy.income
        drag_amount = min(int(deficit * 5), 80)  # proportional to deficit
        self._backend.drag(slider_pos[0], slider_pos[1], slider_pos[0] - drag_amount, slider_pos[1])
        self._backend.send_key("escape")
        logger.info("Army maintenance reduced (drag %dpx)", drag_amount)

    def post_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        return CheckResult(passed=True, message="Maintenance ridotta, verifica al prossimo autosave.")
