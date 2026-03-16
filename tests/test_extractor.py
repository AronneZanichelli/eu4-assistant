import pytest
from eu4_assistant_bot.extractor import StateExtractor


FULL_TREE = {
    "date": "1460.06.01",
    "player": "POR",
    "stability": 2,
    "prestige": 45.5,
    "countries": {
        "POR": {
            "treasury": 230.0,
            "income": 18.0,
            "expenses": 12.0,
            "loan_size": 0.0,
            "land_forcelimit": 30,
            "manpower": 22.0,   # EU4 stores as thousands
            "legitimacy": 95.0,
            "adm_power": 150,
            "dip_power": 120,
            "mil_power": 100,
            "technology": {
                "adm_tech": 5,
                "dip_tech": 5,
                "mil_tech": 6,
            },
            "active_idea_groups": {
                "exploration_ideas": 7,
                "expansion_ideas": 3,
            },
            "free_policies": 2,
            "alliance": ["CAS", "ENG"],
            "overextension_percentage": 35.0,
            "rebel_faction": [
                {"type": "heretic_rebels"},
                {"type": "nationalist_rebels"},
            ],
            "army": [
                {"name": "Exercito", "location": 1297},
                {"name": "Guarda",   "location": 230},
            ],
        }
    },
}


def test_extract_basic_scalars():
    snap = StateExtractor().extract(FULL_TREE)
    assert snap.country == "POR"
    assert snap.eu4_date == "1460.06.01"
    assert snap.stability == 2
    assert snap.prestige == pytest.approx(45.5)


def test_extract_economy():
    snap = StateExtractor().extract(FULL_TREE)
    assert snap.economy.treasury == pytest.approx(230.0)
    assert snap.economy.income == pytest.approx(18.0)


def test_extract_military():
    snap = StateExtractor().extract(FULL_TREE)
    assert snap.military.force_limit == 30
    assert snap.military.manpower == 22000
    assert len(snap.military.armies) == 2


def test_extract_tech():
    snap = StateExtractor().extract(FULL_TREE)
    assert snap.tech.adm_tech == 5
    assert snap.tech.mil_tech == 6
    assert snap.tech.adm_points == 150


def test_extract_ideas():
    snap = StateExtractor().extract(FULL_TREE)
    assert "exploration_ideas" in snap.ideas.completed_groups
    assert snap.ideas.current_group == "expansion_ideas"
    assert snap.ideas.ideas_in_current_group == 3
    assert snap.ideas.free_policies == 2


def test_extract_diplomacy():
    snap = StateExtractor().extract(FULL_TREE)
    assert "CAS" in snap.diplomacy.alliances
    assert "ENG" in snap.diplomacy.alliances


def test_extract_risk():
    snap = StateExtractor().extract(FULL_TREE)
    assert snap.risk.coalition == pytest.approx(0.35)
    assert snap.risk.rebels == pytest.approx(0.4)


def test_extract_legitimacy():
    snap = StateExtractor().extract(FULL_TREE)
    assert snap.legitimacy == pytest.approx(95.0)


def test_extract_empty_tree_returns_safe_defaults():
    snap = StateExtractor().extract({})
    assert snap.country == "UNK"
    assert snap.eu4_date == ""
    assert snap.stability == 0
    assert snap.tech.adm_tech == 0
    assert snap.ideas.completed_groups == []


def test_extract_missing_country_block_returns_defaults():
    snap = StateExtractor().extract({"player": "FRA", "date": "1500.01.01"})
    assert snap.country == "FRA"
    assert snap.economy.treasury == 0.0
    assert snap.military.force_limit == 0


def test_extract_single_army_not_list():
    """army as dict (single entry) should still work."""
    tree = {
        "player": "ENG",
        "countries": {
            "ENG": {
                "army": {"name": "Royal Army", "location": 236},
            }
        },
    }
    snap = StateExtractor().extract(tree)
    assert len(snap.military.armies) == 1


def test_extract_produces_valid_snapshot_json():
    snap = StateExtractor().extract(FULL_TREE)
    import json
    parsed = json.loads(snap.to_json())
    assert parsed["country"] == "POR"
    assert parsed["tech"]["adm_tech"] == 5


# ── M6: regiment composition + war extraction ──────────────────────────────


def test_extract_army_composition():
    tree = {
        "player": "FRA",
        "countries": {
            "FRA": {
                "land_forcelimit": 40,
                "manpower": 30.0,
                "army": {
                    "name": "Armée Royale",
                    "location": 183,
                    "regiment": [
                        {"type": "french_infantry", "home": 183},
                        {"type": "french_infantry", "home": 183},
                        {"type": "latin_cavalry", "home": 183},
                        {"type": "western_artillery", "home": 183},
                    ],
                },
            }
        },
    }
    snap = StateExtractor().extract(tree)
    assert len(snap.military.armies) == 1
    comp = snap.military.armies[0].composition
    assert comp["infantry"] == 2
    assert comp["cavalry"] == 1
    assert comp["artillery"] == 1


def test_extract_wars():
    tree = {
        "player": "FRA",
        "countries": {"FRA": {}},
        "active_war": {
            "name": "FRA vs AUS",
            "attackers": [{"tag": "FRA"}, {"tag": "CAS"}],
            "defenders": [{"tag": "AUS"}, {"tag": "HUN"}],
            "war_score": 35.5,
            "start_date": "1455.03.12",
        },
    }
    snap = StateExtractor().extract(tree)
    assert snap.military.at_war is True
    assert len(snap.military.wars) == 1
    war = snap.military.wars[0]
    assert war.war_name == "FRA vs AUS"
    assert war.our_side == "attacker"
    assert war.war_score == pytest.approx(35.5)


def test_extract_war_as_defender():
    tree = {
        "player": "AUS",
        "countries": {"AUS": {}},
        "active_war": [
            {
                "name": "FRA vs AUS",
                "attackers": [{"tag": "FRA"}],
                "defenders": [{"tag": "AUS"}],
                "war_score": -20.0,
            }
        ],
    }
    snap = StateExtractor().extract(tree)
    assert snap.military.at_war is True
    assert snap.military.wars[0].our_side == "defender"


def test_extract_no_wars():
    snap = StateExtractor().extract(FULL_TREE)
    assert snap.military.at_war is False
    assert snap.military.wars == []
