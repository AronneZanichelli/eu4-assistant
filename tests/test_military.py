from eu4_assistant_bot.military import MilitaryAdvisor, StackScore
from eu4_assistant_bot.models import ArmyState, GameSnapshot, MilitaryState


def _army(inf: int = 0, cav: int = 0, art: int = 0, **kw) -> ArmyState:
    return ArmyState(
        id=kw.get("id", "a1"),
        name=kw.get("name", "Test Army"),
        location=1,
        strength=(inf + cav + art) * 1000,
        composition={"infantry": inf, "cavalry": cav, "artillery": art},
    )


class TestScoreStack:
    def test_full_balanced_stack_is_optimal(self) -> None:
        advisor = MilitaryAdvisor(combat_width=20)
        army = _army(inf=10, cav=4, art=6)
        score = advisor.score_stack(army)
        assert score.total_regiments == 20
        assert score.combat_width_fill == 1.0
        assert score.optimal is True
        assert score.issues == []

    def test_undersized_stack(self) -> None:
        advisor = MilitaryAdvisor(combat_width=30)
        army = _army(inf=5, cav=2, art=3)  # 10/30 = 0.33
        score = advisor.score_stack(army)
        assert score.combat_width_fill < 0.5
        assert "undersized" in score.issues
        assert score.optimal is False

    def test_no_artillery_alert(self) -> None:
        advisor = MilitaryAdvisor(combat_width=20)
        army = _army(inf=10, cav=5, art=0)
        score = advisor.score_stack(army)
        assert "no_artillery" in score.issues

    def test_excess_cavalry(self) -> None:
        advisor = MilitaryAdvisor(combat_width=20)
        army = _army(inf=3, cav=12, art=3)  # cav > 50%
        score = advisor.score_stack(army)
        assert "excess_cavalry" in score.issues

    def test_empty_army(self) -> None:
        advisor = MilitaryAdvisor()
        army = _army(inf=0, cav=0, art=0)
        score = advisor.score_stack(army)
        assert score.total_regiments == 0
        assert "empty_army" in score.issues
        assert score.optimal is False


class TestAssessArmies:
    def test_generates_alerts_for_undersized(self) -> None:
        advisor = MilitaryAdvisor(combat_width=30)
        snapshot = GameSnapshot.empty(country="FRA")
        snapshot.military = MilitaryState(
            force_limit=30, manpower=20000,
            armies=[_army(inf=5, cav=1, art=2, id="a1", name="Petite")],
        )
        alerts = advisor.assess_armies(snapshot)
        assert len(alerts) >= 1
        assert any(a.alert_type == "undersized" for a in alerts)
        assert any(a.severity == "critical" for a in alerts)

    def test_no_alerts_for_optimal_army(self) -> None:
        advisor = MilitaryAdvisor(combat_width=20)
        snapshot = GameSnapshot.empty(country="FRA")
        snapshot.military = MilitaryState(
            force_limit=20, manpower=20000,
            armies=[_army(inf=10, cav=4, art=6)],
        )
        alerts = advisor.assess_armies(snapshot)
        assert len(alerts) == 0


class TestBattleOdds:
    def test_favorable_engagement(self) -> None:
        advisor = MilitaryAdvisor(combat_width=27)
        ours = _army(inf=15, cav=5, art=7)   # 27 total
        enemy = _army(inf=8, cav=2, art=3)   # 13 total
        odds = advisor.evaluate_battle_odds(ours, enemy)
        assert odds.strength_ratio > 1.5
        assert odds.favorable is True
        assert advisor.should_engage(odds) is True
        assert advisor.should_retreat(odds) is False

    def test_unfavorable_retreat(self) -> None:
        advisor = MilitaryAdvisor(combat_width=27)
        ours = _army(inf=4, cav=1, art=1)    # 6 total
        enemy = _army(inf=15, cav=5, art=7)  # 27 total
        odds = advisor.evaluate_battle_odds(ours, enemy)
        assert odds.strength_ratio < 0.6
        assert odds.favorable is False
        assert advisor.should_retreat(odds) is True
        assert advisor.should_engage(odds) is False

    def test_neutral_odds(self) -> None:
        advisor = MilitaryAdvisor(combat_width=27)
        ours = _army(inf=10, cav=3, art=5)   # 18
        enemy = _army(inf=10, cav=3, art=5)  # 18
        odds = advisor.evaluate_battle_odds(ours, enemy)
        assert odds.strength_ratio == 1.0
        assert odds.favorable is False
        assert advisor.should_retreat(odds) is False


class TestRecruitment:
    def test_recommends_when_under_force_limit(self) -> None:
        advisor = MilitaryAdvisor()
        snapshot = GameSnapshot.empty(country="ENG")
        snapshot.military = MilitaryState(
            force_limit=30, manpower=20000,
            armies=[_army(inf=8, cav=2, art=4)],  # 14 regiments
        )
        plan = advisor.recommend_recruitment(snapshot)
        assert plan is not None
        assert plan.infantry_needed + plan.cavalry_needed + plan.artillery_needed == 16
        assert "14/30" in plan.reason

    def test_no_recruitment_at_force_limit(self) -> None:
        advisor = MilitaryAdvisor()
        snapshot = GameSnapshot.empty(country="ENG")
        snapshot.military = MilitaryState(
            force_limit=20, manpower=20000,
            armies=[_army(inf=10, cav=4, art=6)],  # 20 regiments
        )
        plan = advisor.recommend_recruitment(snapshot)
        assert plan is None


class TestPrioritizeTargets:
    def test_peace_target_when_war_score_high(self) -> None:
        from eu4_assistant_bot.models import WarState
        advisor = MilitaryAdvisor()
        snapshot = GameSnapshot.empty(country="FRA")
        war = WarState(
            war_name="FRA vs AUS", attacker="FRA", defender="AUS",
            our_side="attacker", war_score=65.0,
        )
        targets = advisor.prioritize_targets(snapshot, war)
        assert len(targets) >= 1
        assert targets[0].target_type == "peace"

    def test_no_peace_target_when_war_score_low(self) -> None:
        from eu4_assistant_bot.models import WarState
        advisor = MilitaryAdvisor()
        snapshot = GameSnapshot.empty(country="FRA")
        war = WarState(
            war_name="FRA vs AUS", attacker="FRA", defender="AUS",
            our_side="attacker", war_score=20.0,
        )
        targets = advisor.prioritize_targets(snapshot, war)
        assert len(targets) == 0
