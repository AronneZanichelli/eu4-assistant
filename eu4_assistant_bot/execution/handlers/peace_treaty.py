"""Always-confirm handler: peace treaty negotiation.

Peace treaties are NEVER executed automatically.
This handler exists for the confirmation flow but execute() raises NotImplementedError.
"""
from __future__ import annotations

import logging

from ...models import ActionPlan, GameSnapshot
from ..action_handler import ActionHandler, CheckResult, register_handler

logger = logging.getLogger(__name__)


@register_handler
class PeaceTreatyHandler(ActionHandler):
    action_type = "military_peace_gate"
    requires_confirmation = True
    is_critical = True

    def pre_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        if not snapshot.military.at_war:
            return CheckResult(passed=False, message="Non in guerra, pace non applicabile.")
        return CheckResult(passed=True, message="In guerra, trattativa di pace possibile.")

    def execute(self, plan: ActionPlan, snapshot: GameSnapshot) -> None:
        raise NotImplementedError(
            "Le trattative di pace non vengono mai eseguite automaticamente. "
            "Richiedono intervento manuale del giocatore."
        )

    def post_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        return CheckResult(passed=False, message="Peace treaty non eseguibile automaticamente.")
