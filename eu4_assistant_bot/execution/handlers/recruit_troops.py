"""Peacetime handler: recruit regiments via macro builder."""
from __future__ import annotations

import logging

from ...models import ActionPlan, GameSnapshot
from ..action_handler import ActionHandler, CheckResult, register_handler
from ..input_backend import InputBackend

logger = logging.getLogger(__name__)


@register_handler
class RecruitTroopsHandler(ActionHandler):
    action_type = "military_recruit"
    requires_confirmation = False
    is_critical = False

    def __init__(self, backend: InputBackend, max_recruits: int = 8) -> None:
        super().__init__(backend)
        self._max_recruits = max_recruits

    def pre_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        if snapshot.military.manpower <= 0:
            return CheckResult(passed=False, message="Manpower esaurito, impossibile reclutare.")

        total_reg = sum(sum(a.composition.values()) for a in snapshot.military.armies)
        if total_reg >= snapshot.military.force_limit:
            return CheckResult(passed=False, message="Esercito al force limit.")

        return CheckResult(passed=True, message="Manpower e force limit OK.")

    def execute(self, plan: ActionPlan, snapshot: GameSnapshot) -> None:
        total_reg = sum(sum(a.composition.values()) for a in snapshot.military.armies)
        slots = snapshot.military.force_limit - total_reg
        to_recruit = min(slots, self._max_recruits)

        # Open macro builder (hotkey 'b' in EU4)
        self._backend.send_key("b")
        # Click recruit infantry button (placeholder coords — real coords from template)
        recruit_pos = self._backend.locate_template("btn_recruit_infantry")
        if recruit_pos is None:
            recruit_pos = (400, 300)  # fallback
        for _ in range(to_recruit):
            self._backend.click(*recruit_pos)
        # Close macro builder
        self._backend.send_key("escape")
        logger.info("Recruited %d regiments", to_recruit)

    def post_check(self, plan: ActionPlan, snapshot: GameSnapshot) -> CheckResult:
        return CheckResult(passed=True, message="Reclutamento avviato, verifica al prossimo autosave.")
