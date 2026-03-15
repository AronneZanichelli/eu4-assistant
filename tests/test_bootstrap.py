import json
from pathlib import Path

from eu4_assistant_bot.config import BotMode, RiskProfile
from eu4_assistant_bot.main import run


def test_run_bootstraps_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    install = tmp_path / "fake-eu4"
    (install / "common" / "units").mkdir(parents=True)
    (install / "common" / "units" / "unit.txt").write_text("pippo = pluto\n")

    snapshot = tmp_path / "input_snapshot.json"
    snapshot.write_text(
        json.dumps(
            {
                "timestamp": "2026-01-01T00:00:00+00:00",
                "country": "POR",
                "economy": {"treasury": 100, "income": 9, "expenses": 6, "debt": 0},
                "military": {"force_limit": 20, "manpower": 13000, "armies": []},
                "diplomacy": {"truces": [], "alliances": ["ENG"], "ae_map": {}},
                "colonial": {"colonists_free": 1, "active_colonies": []},
                "risk": {"coalition": 0.2, "rebels": 0.1},
            }
        )
    )

    code = run(BotMode.ASSIST, install_path=install, snapshot_json_path=snapshot, risk_profile=RiskProfile.SAFE)

    assert code == 0
    assert (tmp_path / ".eu4-assistant" / "snapshots" / "last_snapshot.json").exists()
    events = tmp_path / ".eu4-assistant" / "events.jsonl"
    assert events.exists()
    event_payload = json.loads(events.read_text().splitlines()[-1])
    assert event_payload["payload"]["snapshot_source"] == "json"
    assert event_payload["payload"]["risk_profile"] == "safe"
    assert "risk_alerts" in event_payload["payload"]
    assert "action_plans" in event_payload["payload"]
    assert "execution_results" in event_payload["payload"]
    assert "execution_summary" in event_payload["payload"]


def test_run_falls_back_to_empty_snapshot_on_invalid_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    install = tmp_path / "fake-eu4"
    (install / "common" / "units").mkdir(parents=True)
    (install / "common" / "units" / "unit.txt").write_text("pippo = pluto\n")

    snapshot = tmp_path / "invalid_snapshot.json"
    snapshot.write_text('{"country": "POR"}')

    code = run(BotMode.ASSIST, install_path=install, snapshot_json_path=snapshot)

    assert code == 0
    event_payload = json.loads((tmp_path / ".eu4-assistant" / "events.jsonl").read_text().splitlines()[-1])
    assert event_payload["payload"]["snapshot_source"] == "fallback_empty"
    assert "missing required field" in event_payload["payload"]["snapshot_error"]


def test_run_uses_save_extract_adapter(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    install = tmp_path / "fake-eu4"
    (install / "common" / "units").mkdir(parents=True)
    (install / "common" / "units" / "unit.txt").write_text("pippo = pluto\n")

    save = tmp_path / "campaign.extract"
    save.write_text(
        "\n".join(
            [
                "timestamp=2026-01-01T00:00:00+00:00",
                "country=POR",
                "income=12",
                "expenses=5",
                "force_limit=24",
                "manpower=15000",
                "coalition=0.2",
                "rebels=0.1",
            ]
        )
    )

    code = run(BotMode.ASSIST, install_path=install, snapshot_save_path=save)

    assert code == 0
    event_payload = json.loads((tmp_path / ".eu4-assistant" / "events.jsonl").read_text().splitlines()[-1])
    assert event_payload["payload"]["snapshot_source"] == "save_extract"
    assert len(event_payload["payload"]["action_plans"]) > 0
    assert event_payload["payload"]["execution_summary"]["executed"] >= 0


def test_run_serializes_risk_codes_as_strings(tmp_path: Path, monkeypatch) -> None:
    """RiskCode Enum values must be serialized as strings in events.jsonl."""
    monkeypatch.chdir(tmp_path)

    install = tmp_path / "fake-eu4"
    (install / "common" / "units").mkdir(parents=True)

    # Snapshot that triggers coalition + debt risks (produces reasons with RiskCode)
    snapshot = tmp_path / "risky_snapshot.json"
    import json as _json
    snapshot.write_text(_json.dumps({
        "timestamp": "2026-01-01T00:00:00+00:00",
        "country": "POR",
        "economy": {"treasury": 10, "income": 5, "expenses": 8, "debt": 200},
        "military": {"force_limit": 20, "manpower": 1000, "armies": []},
        "diplomacy": {"truces": [], "alliances": [], "ae_map": {}},
        "colonial": {"colonists_free": 0, "active_colonies": []},
        "risk": {"coalition": 0.9, "rebels": 0.8},
    }))

    from eu4_assistant_bot.config import BotMode, RiskProfile
    from eu4_assistant_bot.main import run

    code = run(BotMode.ASSIST, install_path=install, snapshot_json_path=snapshot,
               risk_profile=RiskProfile.SAFE)

    assert code == 0
    events_path = tmp_path / ".eu4-assistant" / "events.jsonl"
    raw = events_path.read_text()

    # Must be valid JSON
    event = _json.loads(raw.splitlines()[-1])

    # All reason codes must be plain strings, not dicts or enum reprs
    reasons = event["payload"]["risk_alerts"]["reasons"]
    assert len(reasons) > 0
    for reason in reasons:
        assert isinstance(reason["code"], str), f"Expected str, got {type(reason['code'])}: {reason['code']}"
        assert "." in reason["code"], f"Expected dotted code like 'coalition.high', got: {reason['code']}"
