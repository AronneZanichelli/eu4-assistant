"""Peacetime handler: improve relations to reduce coalition risk."""
from __future__ import annotations

import logging

from ...models import ActionPlan, GameSnapshot
from ..action_handler import ActionHandler, CheckResult, register_handler
from ..input_backend import InputBackend

logger = logging.getLogger(__name__)


@register_handler
class ImproveRelationsHandler(ActionHandler):
    action_type = "diplomacy_reduce_coalition"
    requires_confirmation = False
    is_critical = False

    def __init__(self, backend: InputBackend) -> None:
        super().__init__(backend)

    def pre_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        if snapshot.risk.coalition <= 0:
            return CheckResult(passed=False, message="Nessun rischio coalizione rilevato.")
        return CheckResult(passed=True, message="Coalition risk presente, miglioramento relazioni consigliato.")

    def execute(self, plan: ActionPlan, snapshot: GameSnapshot) -> None:
        # Open diplomacy view
        self._backend.send_key("f1")
        diplomacy_btn = self._backend.locate_template("btn_improve_relations")
        if diplomacy_btn is None:
            diplomacy_btn = (450, 350)
        self._backend.click(*diplomacy_btn)
        self._backend.send_key("escape")
        logger.info("Improve relations action executed")

    def post_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        return CheckResult(passed=True, message="Miglioramento relazioni avviato, verifica al prossimo autosave.")
