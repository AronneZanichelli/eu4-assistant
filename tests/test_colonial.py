from eu4_assistant_bot.colonial import ColonialAdvisor, TRADE_GOOD_VALUES
from eu4_assistant_bot.models import ColonialState, GameSnapshot, ProvinceState


def test_rank_provinces_by_trade_good_and_base_tax() -> None:
    advisor = ColonialAdvisor()
    candidates = [
        ProvinceState(province_id=1, name="Grain Land", base_tax=3.0, trade_good="grain"),
        ProvinceState(province_id=2, name="Gold Mine", base_tax=2.0, trade_good="gold"),
        ProvinceState(province_id=3, name="Spice Isle", base_tax=4.0, trade_good="spices"),
    ]
    rankings = advisor.rank_provinces(candidates)

    assert len(rankings) == 3
    # Spice (6.0 × 4 = 24) > Gold (10.0 × 2 = 20) > Grain (1.5 × 3 = 4.5)
    assert rankings[0].province_id == 3  # spices
    assert rankings[1].province_id == 2  # gold
    assert rankings[2].province_id == 1  # grain
    assert rankings[0].score > rankings[1].score > rankings[2].score


def test_rank_provinces_unknown_trade_good_uses_default() -> None:
    advisor = ColonialAdvisor()
    candidates = [
        ProvinceState(province_id=1, name="Mystery", base_tax=5.0, trade_good="unknown_good"),
    ]
    rankings = advisor.rank_provinces(candidates)
    assert rankings[0].score == 5.0  # default 1.0 × 5


def test_rank_provinces_empty_list() -> None:
    advisor = ColonialAdvisor()
    assert advisor.rank_provinces([]) == []


def test_recommend_colonization_no_colonists() -> None:
    advisor = ColonialAdvisor()
    snapshot = GameSnapshot.empty(country="POR")
    snapshot.colonial = ColonialState(colonists_free=0, total_colonists=2)

    plan = advisor.recommend_colonization(snapshot)
    assert plan is not None
    assert plan.colonists_available == 0
    assert "nessun colono" in plan.reason.lower()


def test_recommend_colonization_free_colonist_no_active() -> None:
    advisor = ColonialAdvisor()
    snapshot = GameSnapshot.empty(country="POR")
    snapshot.colonial = ColonialState(colonists_free=1, total_colonists=2)
    snapshot.provinces = []

    plan = advisor.recommend_colonization(snapshot)
    assert plan is not None
    assert plan.colonists_available == 1
    assert "invia" in plan.reason.lower()


def test_recommend_colonization_free_colonist_with_active() -> None:
    advisor = ColonialAdvisor()
    snapshot = GameSnapshot.empty(country="POR")
    snapshot.colonial = ColonialState(colonists_free=1, total_colonists=2)
    snapshot.provinces = [
        ProvinceState(province_id=100, name="Azores", owner="POR", is_colony=True, colony_progress=400),
    ]

    plan = advisor.recommend_colonization(snapshot)
    assert plan is not None
    assert plan.colonists_available == 1
    assert "1 colonie in corso" in plan.reason


def test_trade_good_values_has_common_goods() -> None:
    for good in ("gold", "spices", "ivory", "sugar", "grain", "fish"):
        assert good in TRADE_GOOD_VALUES
