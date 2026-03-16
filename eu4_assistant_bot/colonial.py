from __future__ import annotations

from dataclasses import dataclass, field

from .models import GameSnapshot, ProvinceState


# ── Trade good values (higher = more valuable for colonization) ──────────────
# Based on EU4 base trade good prices, normalized to a 1-10 scale.
TRADE_GOOD_VALUES: dict[str, float] = {
    "gold": 10.0,
    "spices": 6.0,
    "ivory": 5.0,
    "silk": 5.0,
    "cocoa": 4.5,
    "sugar": 4.0,
    "tobacco": 4.0,
    "coffee": 4.0,
    "fur": 3.5,
    "cotton": 3.5,
    "dyes": 3.0,
    "copper": 3.0,
    "iron": 3.0,
    "tea": 3.0,
    "chinaware": 3.0,
    "cloth": 3.0,
    "salt": 2.5,
    "fish": 2.0,
    "naval_supplies": 2.0,
    "wine": 2.5,
    "wool": 2.0,
    "grain": 1.5,
    "livestock": 1.5,
    "unknown": 1.0,
}

_DEFAULT_GOOD_VALUE = 1.0


# ── Support dataclasses ──────────────────────────────────────────────────────

@dataclass(slots=True)
class ColonyRanking:
    province_id: int
    province_name: str
    trade_good: str
    score: float
    reason: str


@dataclass(slots=True)
class ColonizationPlan:
    target: ColonyRanking | None = None
    colonists_available: int = 0
    reason: str = ""


class ColonialAdvisor:
    """M7 colonial logic: province ranking, colonization recommendations."""

    def rank_provinces(self, candidates: list[ProvinceState]) -> list[ColonyRanking]:
        """Rank uncolonized provinces by value (trade good × base tax).

        Args:
            candidates: Province states that are potential colonization targets
                        (unowned or colony-in-progress provinces).

        Returns:
            List of ColonyRanking sorted by score descending.
        """
        rankings: list[ColonyRanking] = []
        for prov in candidates:
            good_value = TRADE_GOOD_VALUES.get(prov.trade_good, _DEFAULT_GOOD_VALUE)
            base = max(prov.base_tax, 1.0)
            score = round(good_value * base, 2)
            rankings.append(ColonyRanking(
                province_id=prov.province_id,
                province_name=prov.name,
                trade_good=prov.trade_good,
                score=score,
                reason=f"{prov.trade_good} (valore {good_value}) × base tax {base:.0f} = {score:.1f}",
            ))
        rankings.sort(key=lambda r: r.score, reverse=True)
        return rankings

    def recommend_colonization(self, snapshot: GameSnapshot) -> ColonizationPlan | None:
        """Recommend next colonization target if colonists are available.

        Looks at provinces the player owns that are active colonies (in progress)
        and checks if there are free colonists to start new colonies.
        """
        col = snapshot.colonial
        if col.colonists_free <= 0:
            return ColonizationPlan(
                colonists_available=0,
                reason="Nessun colono disponibile.",
            )

        # Find provinces that could be improved (colonies in progress)
        in_progress = [p for p in snapshot.provinces if p.is_colony]
        if in_progress:
            # There are active colonies; check if we can start more
            return ColonizationPlan(
                colonists_available=col.colonists_free,
                reason=f"{col.colonists_free} coloni liberi, {len(in_progress)} colonie in corso.",
            )

        # No colonies in progress and colonists available
        return ColonizationPlan(
            colonists_available=col.colonists_free,
            reason=f"{col.colonists_free} coloni liberi ma nessuna colonia attiva. Invia un colono!",
        )
