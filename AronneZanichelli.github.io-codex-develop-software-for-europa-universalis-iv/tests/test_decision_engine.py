from eu4_assistant_bot.config import DecisionThresholds
from eu4_assistant_bot.decision_engine import DecisionEngine, RiskCode
from eu4_assistant_bot.models import EconomyState, GameSnapshot, MilitaryState, RiskState


def test_recommendation_returns_three_items_when_low_risk() -> None:
    snapshot = GameSnapshot.empty(country="ITA")
    snapshot.economy = EconomyState(treasury=200, income=20, expenses=10, debt=0)
    snapshot.military = MilitaryState(force_limit=30, manpower=28000)
    snapshot.risk = RiskState(coalition=0.2, rebels=0.1)

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
