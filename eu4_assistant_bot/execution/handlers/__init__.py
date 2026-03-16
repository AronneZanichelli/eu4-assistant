"""Concrete action handlers — import all to trigger registration."""

from .engage_battle import EngageBattleHandler
from .improve_relations import ImproveRelationsHandler
from .move_army import MoveArmyHandler
from .peace_treaty import PeaceTreatyHandler
from .recruit_troops import RecruitTroopsHandler
from .reduce_maintenance import ReduceMaintenanceHandler
from .retreat_army import RetreatArmyHandler
from .send_colonist import SendColonistHandler
from .siege_target import SiegeTargetHandler

__all__ = [
    "EngageBattleHandler",
    "ImproveRelationsHandler",
    "MoveArmyHandler",
    "PeaceTreatyHandler",
    "RecruitTroopsHandler",
    "ReduceMaintenanceHandler",
    "RetreatArmyHandler",
    "SendColonistHandler",
    "SiegeTargetHandler",
]
