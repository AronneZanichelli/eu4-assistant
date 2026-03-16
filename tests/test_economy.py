from eu4_assistant_bot.economy import EconomyAdvisor
from eu4_assistant_bot.models import EconomyState, GameSnapshot, TechState, TradeNodeState


class TestMerchantSteering:
    def test_collect_at_highest_value_node(self) -> None:
        advisor = EconomyAdvisor()
        snapshot = GameSnapshot.empty(country="POR")
        snapshot.trade_nodes = [
            TradeNodeState(id="Sevilla", our_power=30.0, total_value=15.0, merchants=1),
            TradeNodeState(id="Ivory Coast", our_power=10.0, total_value=8.0, merchants=1),
        ]
        advice = advisor.recommend_merchant_steering(snapshot)

        assert len(advice) == 2
        assert advice[0].node_id == "Sevilla"
        assert advice[0].action == "collect"
        assert advice[1].node_id == "Ivory Coast"
        assert advice[1].action == "steer"

    def test_no_advice_without_trade_nodes(self) -> None:
        advisor = EconomyAdvisor()
        snapshot = GameSnapshot.empty(country="POR")
        snapshot.trade_nodes = []

        assert advisor.recommend_merchant_steering(snapshot) == []

    def test_single_node_collects(self) -> None:
        advisor = EconomyAdvisor()
        snapshot = GameSnapshot.empty(country="ENG")
        snapshot.trade_nodes = [
            TradeNodeState(id="English Channel", our_power=50.0, total_value=30.0, merchants=1),
        ]
        advice = advisor.recommend_merchant_steering(snapshot)
        assert len(advice) == 1
        assert advice[0].action == "collect"


class TestTechReadiness:
    def test_alerts_when_points_insufficient(self) -> None:
        advisor = EconomyAdvisor()
        snapshot = GameSnapshot.empty(country="FRA")
        snapshot.tech = TechState(adm_tech=5, dip_tech=5, mil_tech=5, adm_points=100, dip_points=800, mil_points=800)

        alerts = advisor.check_tech_readiness(snapshot)

        assert len(alerts) == 1
        assert alerts[0].tech_type == "adm"
        assert alerts[0].points_available == 100
        assert alerts[0].points_needed > 100

    def test_no_alerts_when_points_sufficient(self) -> None:
        advisor = EconomyAdvisor()
        snapshot = GameSnapshot.empty(country="FRA")
        snapshot.tech = TechState(adm_tech=3, dip_tech=3, mil_tech=3, adm_points=700, dip_points=700, mil_points=700)

        alerts = advisor.check_tech_readiness(snapshot)
        assert len(alerts) == 0

    def test_cost_increases_with_level(self) -> None:
        advisor = EconomyAdvisor()
        cost_3 = advisor._estimate_tech_cost(3)
        cost_10 = advisor._estimate_tech_cost(10)
        assert cost_10 > cost_3


class TestBalanceAlert:
    def test_alert_when_balance_low(self) -> None:
        advisor = EconomyAdvisor(balance_threshold=1.0)
        snapshot = GameSnapshot.empty(country="CAS")
        snapshot.economy = EconomyState(treasury=50, income=10, expenses=9.5, debt=0)

        alert = advisor.check_balance(snapshot)
        assert alert is not None
        assert alert.current_balance == 0.5
        assert "basso" in alert.message.lower()

    def test_no_alert_when_balance_healthy(self) -> None:
        advisor = EconomyAdvisor(balance_threshold=1.0)
        snapshot = GameSnapshot.empty(country="CAS")
        snapshot.economy = EconomyState(treasury=100, income=15, expenses=8, debt=0)

        alert = advisor.check_balance(snapshot)
        assert alert is None

    def test_negative_balance_triggers_alert(self) -> None:
        advisor = EconomyAdvisor()
        snapshot = GameSnapshot.empty(country="OTT")
        snapshot.economy = EconomyState(treasury=20, income=5, expenses=8, debt=0)

        alert = advisor.check_balance(snapshot)
        assert alert is not None
        assert alert.current_balance < 0
