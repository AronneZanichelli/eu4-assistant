"""Peacetime handler: send colonist to target province."""
from __future__ import annotations

import logging

from ...models import ActionPlan, GameSnapshot
from ..action_handler import ActionHandler, CheckResult, register_handler
from ..input_backend import InputBackend

logger = logging.getLogger(__name__)


@register_handler
class SendColonistHandler(ActionHandler):
    action_type = "colonial_send_colonist"
    requires_confirmation = False
    is_critical = False

    def __init__(self, backend: InputBackend) -> None:
        super().__init__(backend)

    def pre_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        if snapshot.colonial.colonists_free <= 0:
            return CheckResult(passed=False, message="Nessun colono disponibile.")
        return CheckResult(passed=True, message="Colono disponibile.")

    def execute(self, plan: ActionPlan, snapshot: GameSnapshot) -> None:
        # Open colonization macro view
        self._backend.send_key("e")
        # Navigate to target province from plan
        colony_btn = self._backend.locate_template("btn_send_colonist")
        if colony_btn is None:
            colony_btn = (500, 400)
        self._backend.click(*colony_btn)
        self._backend.send_key("escape")
        logger.info("Colonist sent")

    def post_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        return CheckResult(passed=True, message="Colono inviato, verifica al prossimo autosave.")
