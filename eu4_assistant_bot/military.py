from __future__ import annotations

from dataclasses import dataclass, field

from .models import ArmyState, BattleOdds, GameSnapshot, MilitaryState, WarState


# ── Support dataclasses ─────────────────────────────────────────────────────

@dataclass(slots=True)
class StackScore:
    army_id: str
    total_regiments: int
    combat_width_fill: float   # ratio vs combat width
    infantry_ratio: float
    cavalry_ratio: float
    artillery_ratio: float
    optimal: bool              # True if composition is balanced
    issues: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ArmyAlert:
    army_id: str
    army_name: str
    alert_type: str            # "undersized" | "no_artillery" | "excess_cavalry"
    message: str
    severity: str              # "warning" | "critical"


@dataclass(slots=True)
class RecruitmentPlan:
    infantry_needed: int = 0
    cavalry_needed: int = 0
    artillery_needed: int = 0
    reason: str = ""


@dataclass(slots=True)
class WarTarget:
    province_id: int = 0
    target_type: str = ""      # "siege" | "engage" | "defend"
    priority: float = 0.0
    reason: str = ""


# ── Thresholds ───────────────────────────────────────────────────────────────

_DEFAULT_COMBAT_WIDTH = 27        # early-game default
_ENGAGE_THRESHOLD = 1.5           # strength ratio to engage
_RETREAT_THRESHOLD = 0.6          # strength ratio to retreat
_UNDERSIZED_FILL = 0.5            # below this → undersized alert
_EXCESS_CAVALRY_RATIO = 0.5       # above this → excess cavalry
_IDEAL_INF_RATIO = 0.50
_IDEAL_CAV_RATIO = 0.20
_IDEAL_ART_RATIO = 0.30
_COMPOSITION_TOLERANCE = 0.15     # allowed deviation from ideal ratio


class MilitaryAdvisor:
    """M6 military logic: stack scoring, army assessment, wartime routing."""

    def __init__(
        self,
        combat_width: int = _DEFAULT_COMBAT_WIDTH,
        engage_threshold: float = _ENGAGE_THRESHOLD,
        retreat_threshold: float = _RETREAT_THRESHOLD,
    ):
        self.combat_width = combat_width
        self.engage_threshold = engage_threshold
        self.retreat_threshold = retreat_threshold

    # ── Peacetime ────────────────────────────────────────────────────────────

    def score_stack(self, army: ArmyState) -> StackScore:
        """Score an army stack against combat width and ideal composition."""
        comp = army.composition
        inf = comp.get("infantry", 0)
        cav = comp.get("cavalry", 0)
        art = comp.get("artillery", 0)
        total = inf + cav + art

        if total == 0:
            return StackScore(
                army_id=army.id,
                total_regiments=0,
                combat_width_fill=0.0,
                infantry_ratio=0.0,
                cavalry_ratio=0.0,
                artillery_ratio=0.0,
                optimal=False,
                issues=["empty_army"],
            )

        fill = total / max(self.combat_width, 1)
        inf_r = inf / total
        cav_r = cav / total
        art_r = art / total

        issues: list[str] = []
        if fill < _UNDERSIZED_FILL:
            issues.append("undersized")
        if art == 0 and total >= 4:
            issues.append("no_artillery")
        if cav_r > _EXCESS_CAVALRY_RATIO:
            issues.append("excess_cavalry")

        optimal = (
            len(issues) == 0
            and abs(inf_r - _IDEAL_INF_RATIO) <= _COMPOSITION_TOLERANCE
            and abs(cav_r - _IDEAL_CAV_RATIO) <= _COMPOSITION_TOLERANCE
            and abs(art_r - _IDEAL_ART_RATIO) <= _COMPOSITION_TOLERANCE
        )

        return StackScore(
            army_id=army.id,
            total_regiments=total,
            combat_width_fill=round(fill, 3),
            infantry_ratio=round(inf_r, 3),
            cavalry_ratio=round(cav_r, 3),
            artillery_ratio=round(art_r, 3),
            optimal=optimal,
            issues=issues,
        )

    def assess_armies(self, snapshot: GameSnapshot) -> list[ArmyAlert]:
        """Generate alerts for armies with composition issues."""
        alerts: list[ArmyAlert] = []
        for army in snapshot.military.armies:
            score = self.score_stack(army)
            for issue in score.issues:
                severity = "critical" if issue in ("undersized", "empty_army") else "warning"
                alerts.append(ArmyAlert(
                    army_id=army.id,
                    army_name=army.name,
                    alert_type=issue,
                    message=_ALERT_MESSAGES.get(issue, f"Problema: {issue}"),
                    severity=severity,
                ))
        return alerts

    def recommend_recruitment(self, snapshot: GameSnapshot) -> RecruitmentPlan | None:
        """Recommend recruitment if total regiments are below force limit."""
        mil = snapshot.military
        total_regiments = sum(
            sum(a.composition.values()) for a in mil.armies
        )
        if total_regiments >= mil.force_limit:
            return None

        deficit = mil.force_limit - total_regiments
        # Distribute deficit using ideal ratios
        inf_need = round(deficit * _IDEAL_INF_RATIO)
        cav_need = round(deficit * _IDEAL_CAV_RATIO)
        art_need = deficit - inf_need - cav_need  # remainder to artillery

        return RecruitmentPlan(
            infantry_needed=max(inf_need, 0),
            cavalry_needed=max(cav_need, 0),
            artillery_needed=max(art_need, 0),
            reason=f"Sotto force limit: {total_regiments}/{mil.force_limit} reggimenti.",
        )

    # ── Wartime ──────────────────────────────────────────────────────────────

    def evaluate_battle_odds(self, our: ArmyState, enemy: ArmyState) -> BattleOdds:
        """Compare two armies and determine if engagement is favorable."""
        our_total = sum(our.composition.values()) if our.composition else our.strength
        enemy_total = sum(enemy.composition.values()) if enemy.composition else enemy.strength
        ratio = our_total / max(enemy_total, 1)
        fill = our_total / max(self.combat_width, 1)

        return BattleOdds(
            our_strength=our_total,
            enemy_strength=enemy_total,
            our_combat_width_fill=round(fill, 3),
            strength_ratio=round(ratio, 3),
            favorable=ratio >= self.engage_threshold,
        )

    def should_engage(self, odds: BattleOdds) -> bool:
        """Return True if the battle odds favor engagement."""
        return odds.strength_ratio >= self.engage_threshold

    def should_retreat(self, odds: BattleOdds) -> bool:
        """Return True if the battle odds warrant retreat."""
        return odds.strength_ratio <= self.retreat_threshold

    def prioritize_targets(
        self, snapshot: GameSnapshot, war: WarState
    ) -> list[WarTarget]:
        """Rank war targets by priority. Placeholder for province-level routing."""
        # M6 provides the framework; full province-level routing needs M8 executor
        targets: list[WarTarget] = []
        if war.war_score >= 50.0:
            targets.append(WarTarget(
                province_id=0,
                target_type="peace",
                priority=0.97,
                reason=f"War score {war.war_score:.0f}%: valuta trattativa di pace.",
            ))
        return targets


# ── Alert message templates ──────────────────────────────────────────────────

_ALERT_MESSAGES: dict[str, str] = {
    "undersized": "Esercito sotto-dimensionato: meno della metà del combat width.",
    "no_artillery": "Esercito senza artiglieria: penalità assedio e danno ridotto.",
    "excess_cavalry": "Troppa cavalleria (>50%): penalità in battaglia per cavalry ratio.",
    "empty_army": "Esercito vuoto: nessun reggimento assegnato.",
}
