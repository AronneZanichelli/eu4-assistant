"""Wartime handler (stub): siege enemy provinces."""
from __future__ import annotations

import logging

from ...models import ActionPlan, GameSnapshot
from ..action_handler import ActionHandler, CheckResult, register_handler

logger = logging.getLogger(__name__)


@register_handler
class SiegeTargetHandler(ActionHandler):
    action_type = "military_siege"
    requires_confirmation = False
    is_critical = False

    def pre_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        if not snapshot.military.at_war:
            return CheckResult(passed=False, message="Non in guerra.")
        return CheckResult(passed=True, message="In guerra, assedio possibile.")

    def execute(self, plan: ActionPlan, snapshot: GameSnapshot) -> None:
        logger.info("SiegeTargetHandler: navigazione mappa non ancora implementata")

    def post_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        return CheckResult(passed=True, message="Stub: assedio registrato.")
