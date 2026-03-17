"""Tests for DecisionEngine risk evaluation and recommendations."""

from eu4_assistant_bot.config import DecisionThresholds
from eu4_assistant_bot.decision_engine import DecisionEngine, RiskCode
from eu4_assistant_bot.models import (
    ArmyState,
    ColonialState,
    DiplomacyState,
    EconomyState,
    GameSnapshot,
    MilitaryState,
    RiskState,
    TechState,
    TradeNodeState,
)


def test_recommendation_returns_three_items_when_low_risk() -> None:
    snapshot = GameSnapshot.empty(country="ITA")
    snapshot.economy = EconomyState(treasury=200, income=20, expenses=10, debt=0)
    # 27k strength / 30k force limit = 90% — well above 50% threshold
    snapshot.military = MilitaryState(
        force_limit=30,
        manpower=28000,
        armies=[ArmyState(strength=27000)],
    )
    snapshot.risk = RiskState(coalition=0.2, rebels=0.1)
    snapshot.diplomacy = DiplomacyState(active_wars=0)

    recommendations = DecisionEngine().recommend(snapshot)

    assert len(recommendations) == 3
    assert recommendations[0].priority >= recommendations[1].priority


def test_recommendation_flags_high_risks_with_reason_codes() -> None:
    snapshot = GameSnapshot.empty(country="VEN")
    snapshot.economy = EconomyState(treasury=50, income=8, expenses=12, debt=400)
    snapshot.military = MilitaryState(force_limit=35, manpower=2000)
    snapshot.risk = RiskState(coalition=0.85, rebels=0.7)

    risks = DecisionEngine().evaluate_risks(snapshot)

    assert risks.coalition_risk is True
    assert risks.debt_risk is True
    assert risks.manpower_risk is True
    assert risks.rebels_risk is True
    codes = {reason.code for reason in risks.reasons}
    assert RiskCode.COALITION_HIGH in codes
    assert RiskCode.DEBT_NEGATIVE_BALANCE in codes
    assert RiskCode.MANPOWER_LOW in codes
    assert RiskCode.REBELS_HIGH in codes


def test_thresholds_are_configurable() -> None:
    snapshot = GameSnapshot.empty(country="CAS")
    snapshot.economy = EconomyState(treasury=120, income=10, expenses=9, debt=100)
    snapshot.military = MilitaryState(force_limit=20, manpower=3500)
    snapshot.risk = RiskState(coalition=0.55, rebels=0.5)

    engine = DecisionEngine(
        DecisionThresholds(
            coalition_risk_threshold=0.5,
            debt_to_income_threshold=8,
            manpower_ratio_threshold=0.2,
            rebels_risk_threshold=0.4,
        )
    )
    risks = engine.evaluate_risks(snapshot)

    assert risks.coalition_risk is True
    assert risks.debt_risk is True
    assert risks.manpower_risk is True
    assert risks.rebels_risk is True


# ── M6 military tests ─────────────────────────────────────────────────────────

def test_evaluate_military_army_below_force_limit() -> None:
    snap = GameSnapshot.empty("FRA")
    # Force limit 40 → 40k threshold; 10 armies × 1k = 10k (25% = below 50%)
    snap.military = MilitaryState(
        force_limit=40,
        manpower=30000,
        armies=[ArmyState(strength=1000) for _ in range(10)],
    )
    snap.diplomacy = DiplomacyState(active_wars=0)

    engine = DecisionEngine()
    reasons = engine.evaluate_military(snap)
    codes = {r.code for r in reasons}

    assert RiskCode.ARMY_BELOW_FORCE_LIMIT in codes


def test_evaluate_military_no_alert_when_armies_sufficient() -> None:
    snap = GameSnapshot.empty("ENG")
    # Force limit 30 → 30k threshold; 25k = 83% (above 50%)
    snap.military = MilitaryState(
        force_limit=30,
        manpower=20000,
        armies=[ArmyState(strength=25000)],
    )
    snap.diplomacy = DiplomacyState(active_wars=0)

    reasons = DecisionEngine().evaluate_military(snap)
    codes = {r.code for r in reasons}

    assert RiskCode.ARMY_BELOW_FORCE_LIMIT not in codes


def test_evaluate_military_army_fragmented() -> None:
    snap = GameSnapshot.empty("POR")
    snap.military = MilitaryState(
        force_limit=20,
        manpower=15000,
        armies=[ArmyState(strength=1000) for _ in range(5)],  # 5 small armies
    )
    snap.diplomacy = DiplomacyState(active_wars=0)

    reasons = DecisionEngine().evaluate_military(snap)
    codes = {r.code for r in reasons}

    assert RiskCode.ARMY_FRAGMENTED in codes


def test_evaluate_military_wartime_manpower_low() -> None:
    snap = GameSnapshot.empty("OTT")
    snap.military = MilitaryState(force_limit=50, manpower=5000, armies=[ArmyState(strength=30000)])
    snap.diplomacy = DiplomacyState(active_wars=2)  # at war

    engine = DecisionEngine(DecisionThresholds(wartime_manpower_min=10_000))
    reasons = engine.evaluate_military(snap)
    codes = {r.code for r in reasons}

    assert RiskCode.WARTIME_MANPOWER_LOW in codes


def test_evaluate_military_wartime_no_alert_when_manpower_ok() -> None:
    snap = GameSnapshot.empty("SPA")
    snap.military = MilitaryState(force_limit=50, manpower=25000, armies=[ArmyState(strength=40000)])
    snap.diplomacy = DiplomacyState(active_wars=1)

    reasons = DecisionEngine().evaluate_military(snap)
    codes = {r.code for r in reasons}

    assert RiskCode.WARTIME_MANPOWER_LOW not in codes
    assert RiskCode.ARMY_BELOW_FORCE_LIMIT not in codes  # wartime check skips this


def test_recommend_includes_wartime_reinforce_recommendation() -> None:
    snap = GameSnapshot.empty("MOS")
    snap.military = MilitaryState(force_limit=40, manpower=3000, armies=[ArmyState(strength=20000)])
    snap.diplomacy = DiplomacyState(active_wars=1)

    recs = DecisionEngine().recommend(snap)
    titles = [r.title for r in recs]

    assert any("Rinforza" in t for t in titles)


def test_recommend_army_health_in_peacetime() -> None:
    snap = GameSnapshot.empty("AUS")
    # 5k / 40k = 12.5% < 50% threshold, peacetime
    snap.military = MilitaryState(force_limit=40, manpower=20000, armies=[ArmyState(strength=5000)])
    snap.diplomacy = DiplomacyState(active_wars=0)
    snap.economy = EconomyState(treasury=200, income=20, expenses=10, debt=0)

    recs = DecisionEngine().recommend(snap)
    titles = [r.title for r in recs]

    assert any("force limit" in t.lower() or "Recluta" in t for t in titles)


def test_build_action_plans_maps_recommendations() -> None:
    snapshot = GameSnapshot.empty(country="VEN")
    snapshot.economy = EconomyState(treasury=50, income=8, expenses=12, debt=400)
    snapshot.military = MilitaryState(force_limit=35, manpower=2000)
    snapshot.risk = RiskState(coalition=0.85, rebels=0.7)

    plans = DecisionEngine().build_action_plans(snapshot)

    assert len(plans) == 3
    action_types = {plan.action_type for plan in plans}
    assert "diplomacy_reduce_coalition" in action_types
    assert "economy_stabilize_budget" in action_types
    assert "military_recover_manpower" in action_types


# ── M7 colonial tests ──────────────────────────────────────────────────────────

def test_evaluate_colonial_idle_colonist() -> None:
    snap = GameSnapshot.empty("POR")
    snap.colonial = ColonialState(colonists_free=2, active_colonies=[])

    reasons = DecisionEngine().evaluate_colonial(snap)
    codes = {r.code for r in reasons}

    assert RiskCode.COLONIST_IDLE in codes


def test_evaluate_colonial_no_alert_when_colonist_deployed() -> None:
    snap = GameSnapshot.empty("SPA")
    snap.colonial = ColonialState(colonists_free=1, active_colonies=[{"province_id": 901}])

    reasons = DecisionEngine().evaluate_colonial(snap)
    codes = {r.code for r in reasons}

    assert RiskCode.COLONIST_IDLE not in codes


def test_evaluate_colonial_no_alert_when_no_colonists() -> None:
    snap = GameSnapshot.empty("ENG")
    snap.colonial = ColonialState(colonists_free=0, active_colonies=[])

    reasons = DecisionEngine().evaluate_colonial(snap)

    assert reasons == []


def test_colonial_risk_propagates_to_evaluate_risks() -> None:
    snap = GameSnapshot.empty("POR")
    snap.colonial = ColonialState(colonists_free=1, active_colonies=[])

    alerts = DecisionEngine().evaluate_risks(snap)

    assert alerts.colonial_risk is True
    codes = {r.code for r in alerts.reasons}
    assert RiskCode.COLONIST_IDLE in codes


def test_recommend_includes_colonial_recommendation() -> None:
    snap = GameSnapshot.empty("POR")
    snap.colonial = ColonialState(colonists_free=1, active_colonies=[])
    snap.economy = EconomyState(treasury=200, income=20, expenses=10, debt=0)
    snap.military = MilitaryState(force_limit=30, manpower=20000, armies=[ArmyState(strength=25000)])
    snap.diplomacy = DiplomacyState(active_wars=0)
    snap.risk = RiskState(coalition=0.1, rebels=0.1)

    recs = DecisionEngine().recommend(snap)
    titles = [r.title for r in recs]

    assert any("colonist" in t.lower() or "Invia" in t for t in titles)


# ── M7 economy advanced tests ──────────────────────────────────────────────────

def test_evaluate_economy_adv_merchant_undeployed() -> None:
    snap = GameSnapshot.empty("GEN")
    snap.trade_nodes = [
        TradeNodeState(id="genoa", our_power=20.0, total_value=10.0, merchants=0),
        TradeNodeState(id="venice", our_power=15.0, total_value=8.0, merchants=1),
    ]

    reasons = DecisionEngine().evaluate_economy_adv(snap)
    codes = {r.code for r in reasons}

    assert RiskCode.MERCHANT_UNDEPLOYED in codes


def test_evaluate_economy_adv_no_alert_when_merchants_deployed() -> None:
    snap = GameSnapshot.empty("VEN")
    snap.trade_nodes = [
        TradeNodeState(id="venice", our_power=30.0, total_value=12.0, merchants=1),
    ]

    reasons = DecisionEngine().evaluate_economy_adv(snap)
    codes = {r.code for r in reasons}

    assert RiskCode.MERCHANT_UNDEPLOYED not in codes


def test_evaluate_economy_adv_no_alert_low_value_node() -> None:
    """Nodes below the minimum value threshold should not trigger the alert."""
    snap = GameSnapshot.empty("VEN")
    snap.trade_nodes = [
        TradeNodeState(id="small_node", our_power=5.0, total_value=1.0, merchants=0),
    ]

    reasons = DecisionEngine().evaluate_economy_adv(snap)
    codes = {r.code for r in reasons}

    assert RiskCode.MERCHANT_UNDEPLOYED not in codes


def test_evaluate_economy_adv_tech_affordable() -> None:
    snap = GameSnapshot.empty("FRA")
    snap.tech = TechState(adm_tech=5, dip_tech=5, mil_tech=5, adm_points=200, dip_points=50, mil_points=80)

    reasons = DecisionEngine().evaluate_economy_adv(snap)
    codes = {r.code for r in reasons}

    assert RiskCode.TECH_AFFORDABLE in codes


def test_evaluate_economy_adv_no_tech_alert_when_points_low() -> None:
    snap = GameSnapshot.empty("FRA")
    snap.tech = TechState(adm_tech=5, dip_tech=5, mil_tech=5, adm_points=50, dip_points=80, mil_points=60)

    reasons = DecisionEngine().evaluate_economy_adv(snap)
    codes = {r.code for r in reasons}

    assert RiskCode.TECH_AFFORDABLE not in codes


def test_economy_adv_risk_propagates_to_evaluate_risks() -> None:
    snap = GameSnapshot.empty("GEN")
    snap.tech = TechState(adm_points=200)

    alerts = DecisionEngine().evaluate_risks(snap)

    assert alerts.economy_adv_risk is True


def test_recommend_includes_tech_recommendation() -> None:
    snap = GameSnapshot.empty("FRA")
    snap.tech = TechState(adm_points=200)
    snap.economy = EconomyState(treasury=200, income=20, expenses=10, debt=0)
    snap.military = MilitaryState(force_limit=30, manpower=20000, armies=[ArmyState(strength=25000)])
    snap.diplomacy = DiplomacyState(active_wars=0)
    snap.risk = RiskState(coalition=0.1, rebels=0.1)

    recs = DecisionEngine().recommend(snap)
    titles = [r.title for r in recs]

    assert any("tech" in t.lower() or "punti" in t.lower() or "Investi" in t for t in titles)
