from eu4_assistant_bot.config import DecisionThresholds
from eu4_assistant_bot.decision_engine import DecisionEngine, RiskCode
from eu4_assistant_bot.models import (
    ArmyState,
    ColonialState,
    EconomyState,
    GameSnapshot,
    MilitaryState,
    RiskState,
    TechState,
    TradeNodeState,
    WarState,
)


def _full_army(army_id: str = "a1", name: str = "Main Army", regiments: int = 30) -> ArmyState:
    """Helper: create an army at force limit with balanced composition."""
    inf = round(regiments * 0.5)
    cav = round(regiments * 0.2)
    art = regiments - inf - cav
    return ArmyState(
        id=army_id, name=name, location=1, strength=regiments * 1000,
        composition={"infantry": inf, "cavalry": cav, "artillery": art},
    )


def test_recommendation_returns_three_items_when_low_risk() -> None:
    snapshot = GameSnapshot.empty(country="ITA")
    snapshot.economy = EconomyState(treasury=200, income=20, expenses=10, debt=0)
    snapshot.military = MilitaryState(
        force_limit=30, manpower=28000, armies=[_full_army(regiments=30)],
    )
    snapshot.risk = RiskState(coalition=0.2, rebels=0.1)
    # Give enough tech/points to avoid tech alerts
    snapshot.tech = TechState(adm_tech=5, dip_tech=5, mil_tech=5, adm_points=700, dip_points=700, mil_points=700)

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


# ── M6: Military advisor integration tests ──────────────────────────────────


def test_wartime_peace_gate_recommendation() -> None:
    snapshot = GameSnapshot.empty(country="FRA")
    snapshot.economy = EconomyState(treasury=200, income=20, expenses=10, debt=0)
    snapshot.military = MilitaryState(
        force_limit=30, manpower=25000,
        armies=[_full_army(regiments=30)],
        wars=[WarState(
            war_name="FRA vs AUS", attacker="FRA", defender="AUS",
            our_side="attacker", war_score=60.0,
        )],
        at_war=True,
    )
    snapshot.risk = RiskState(coalition=0.2, rebels=0.1)

    recs = DecisionEngine().recommend(snapshot)
    titles = [r.title for r in recs]
    assert any("pace" in t.lower() for t in titles)


def test_peacetime_army_alert_recommendation() -> None:
    snapshot = GameSnapshot.empty(country="ENG")
    snapshot.economy = EconomyState(treasury=200, income=20, expenses=10, debt=0)
    # Undersized army: 5 regiments vs combat width 27
    snapshot.military = MilitaryState(
        force_limit=30, manpower=25000,
        armies=[ArmyState(
            id="a1", name="Weak Army", location=1, strength=5000,
            composition={"infantry": 3, "cavalry": 1, "artillery": 1},
        )],
    )
    snapshot.risk = RiskState(coalition=0.2, rebels=0.1)

    recs = DecisionEngine().recommend(snapshot)
    categories = [r.category for r in recs]
    assert "military" in categories


def test_recruitment_recommendation_when_under_force_limit() -> None:
    snapshot = GameSnapshot.empty(country="POR")
    snapshot.economy = EconomyState(treasury=200, income=15, expenses=8, debt=0)
    snapshot.military = MilitaryState(
        force_limit=25, manpower=20000,
        armies=[ArmyState(
            id="a1", name="Small", location=1, strength=10000,
            composition={"infantry": 5, "cavalry": 2, "artillery": 3},
        )],
    )
    snapshot.risk = RiskState(coalition=0.1, rebels=0.1)

    recs = DecisionEngine().recommend(snapshot)
    titles = [r.title for r in recs]
    assert any("recluta" in t.lower() for t in titles)


# ── M7: Colonial + Economy advisor integration tests ─────────────────────────


def test_colonial_recommendation_when_colonist_free() -> None:
    snapshot = GameSnapshot.empty(country="POR")
    snapshot.economy = EconomyState(treasury=200, income=15, expenses=8, debt=0)
    snapshot.military = MilitaryState(
        force_limit=20, manpower=15000, armies=[_full_army(regiments=20)],
    )
    snapshot.risk = RiskState(coalition=0.1, rebels=0.1)
    snapshot.tech = TechState(adm_tech=5, dip_tech=5, mil_tech=5, adm_points=700, dip_points=700, mil_points=700)
    snapshot.colonial = ColonialState(colonists_free=1, total_colonists=2)

    recs = DecisionEngine().recommend(snapshot)
    categories = [r.category for r in recs]
    assert "colonial" in categories


def test_economy_balance_alert_recommendation() -> None:
    snapshot = GameSnapshot.empty(country="CAS")
    snapshot.economy = EconomyState(treasury=50, income=8, expenses=7.5, debt=0)
    snapshot.military = MilitaryState(
        force_limit=20, manpower=15000, armies=[_full_army(regiments=20)],
    )
    snapshot.risk = RiskState(coalition=0.1, rebels=0.1)
    snapshot.tech = TechState(adm_tech=5, dip_tech=5, mil_tech=5, adm_points=700, dip_points=700, mil_points=700)

    recs = DecisionEngine().recommend(snapshot)
    titles = [r.title for r in recs]
    assert any("bilancio" in t.lower() for t in titles)


def test_merchant_recommendation_with_trade_nodes() -> None:
    snapshot = GameSnapshot.empty(country="ENG")
    snapshot.economy = EconomyState(treasury=200, income=20, expenses=10, debt=0)
    snapshot.military = MilitaryState(
        force_limit=25, manpower=20000, armies=[_full_army(regiments=25)],
    )
    snapshot.risk = RiskState(coalition=0.1, rebels=0.1)
    snapshot.tech = TechState(adm_tech=5, dip_tech=5, mil_tech=5, adm_points=700, dip_points=700, mil_points=700)
    snapshot.trade_nodes = [
        TradeNodeState(id="English Channel", our_power=50.0, total_value=30.0, merchants=1),
        TradeNodeState(id="North Sea", our_power=20.0, total_value=10.0, merchants=1),
    ]

    recs = DecisionEngine().recommend(snapshot)
    titles = " ".join(r.title.lower() for r in recs)
    assert "mercante" in titles


def test_tech_alert_recommendation() -> None:
    snapshot = GameSnapshot.empty(country="FRA")
    snapshot.economy = EconomyState(treasury=200, income=20, expenses=10, debt=0)
    snapshot.military = MilitaryState(
        force_limit=30, manpower=25000, armies=[_full_army(regiments=30)],
    )
    snapshot.risk = RiskState(coalition=0.1, rebels=0.1)
    # ADM low on points
    snapshot.tech = TechState(adm_tech=8, dip_tech=5, mil_tech=5, adm_points=100, dip_points=700, mil_points=700)

    recs = DecisionEngine().recommend(snapshot)
    titles = " ".join(r.title.lower() for r in recs)
    assert "tech" in titles
