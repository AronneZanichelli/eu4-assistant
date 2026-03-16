"""Wartime handler (stub): move armies toward front."""
from __future__ import annotations

import logging

from ...models import ActionPlan, GameSnapshot
from ..action_handler import ActionHandler, CheckResult, register_handler

logger = logging.getLogger(__name__)


@register_handler
class MoveArmyHandler(ActionHandler):
    action_type = "military_move_army"
    requires_confirmation = False
    is_critical = False

    def pre_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        if not snapshot.military.at_war:
            return CheckResult(passed=False, message="Non in guerra, movimento verso fronte non applicabile.")
        if not snapshot.military.armies:
            return CheckResult(passed=False, message="Nessun esercito disponibile.")
        return CheckResult(passed=True, message="In guerra con eserciti disponibili.")

    def execute(self, plan: ActionPlan, snapshot: GameSnapshot) -> None:
        logger.info("MoveArmyHandler: navigazione mappa non ancora implementata")

    def post_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        return CheckResult(passed=True, message="Stub: movimento esercito registrato.")
