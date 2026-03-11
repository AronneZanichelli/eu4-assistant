from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import BotMode, RiskProfile, build_config
from .decision_engine import DecisionEngine
from .executor import ActionExecutor
from .models import GameSnapshot
from .parser import EU4RulesLoader
from .save_adapter import SaveAdapterError, SaveSnapshotAdapter
from .state_reader import SnapshotReadError, SnapshotReader
from .telemetry import emit_event, setup_logging


def run(
    mode: BotMode,
    install_path: Path | None = None,
    snapshot_json_path: Path | None = None,
    snapshot_save_path: Path | None = None,
    risk_profile: RiskProfile = RiskProfile.BALANCED,
) -> int:
    config = build_config(mode, risk_profile=risk_profile)
    if install_path:
        config.eu4_install_path = install_path

    log_file = setup_logging(config.data_dir / "logs", level=config.log_level)
    logger = logging.getLogger("eu4-assistant")
    logger.info("Starting EU4 Assistant in mode: %s", mode.value)

    loader = EU4RulesLoader(config.eu4_install_path)
    rules_index = loader.load_rules_index()

    snapshot_source = "empty"
    snapshot_error: str | None = None
    if snapshot_json_path:
        try:
            snapshot = SnapshotReader().read_json_snapshot(snapshot_json_path)
            snapshot_source = "json"
        except SnapshotReadError as exc:
            snapshot = GameSnapshot.empty(country="TBD")
            snapshot_source = "fallback_empty"
            snapshot_error = str(exc)
            logger.warning("Snapshot JSON adapter fallback: %s", exc)
    elif snapshot_save_path:
        try:
            snapshot = SaveSnapshotAdapter().read_save_extract(snapshot_save_path)
            snapshot_source = "save_extract"
        except SaveAdapterError as exc:
            snapshot = GameSnapshot.empty(country="TBD")
            snapshot_source = "fallback_empty"
            snapshot_error = str(exc)
            logger.warning("Snapshot save adapter fallback: %s", exc)
    else:
        snapshot = GameSnapshot.empty(country="TBD")

    snapshot_path = config.data_dir / "snapshots" / "last_snapshot.json"
    snapshot.save(snapshot_path)

    engine = DecisionEngine(thresholds=config.decision)
    risks = engine.evaluate_risks(snapshot)
    recommendations = engine.recommend(snapshot)
    action_plans = engine.build_action_plans(snapshot)
    execution_results = ActionExecutor().simulate(action_plans, mode=mode)

    events_path = config.data_dir / "events.jsonl"
    emit_event(
        events_path,
        "startup",
        {
            "mode": mode.value,
            "risk_profile": risk_profile.value,
            "rules_index": {
                "units_files": len(rules_index.units),
                "ideas_files": len(rules_index.ideas),
                "modifiers_files": len(rules_index.modifiers),
            },
            "snapshot_path": str(snapshot_path),
            "snapshot_source": snapshot_source,
            "snapshot_error": snapshot_error,
            "log_file": str(log_file),
            "risk_alerts": {
                "coalition_risk": risks.coalition_risk,
                "debt_risk": risks.debt_risk,
                "manpower_risk": risks.manpower_risk,
                "rebels_risk": risks.rebels_risk,
                "reasons": [
                    {
                        "code": reason.code,
                        "severity": reason.severity,
                        "message": reason.message,
                        "current_value": reason.current_value,
                        "threshold_value": reason.threshold_value,
                    }
                    for reason in risks.reasons
                ],
            },
            "action_plans": [
                {
                    "id": plan.id,
                    "action_type": plan.action_type,
                    "priority": plan.priority,
                    "confidence": plan.confidence,
                    "expected_outcome": plan.expected_outcome,
                    "requires_confirmation": plan.requires_confirmation,
                }
                for plan in action_plans
            ],
            "execution_results": [
                {
                    "plan_id": result.plan_id,
                    "action_type": result.action_type,
                    "status": result.status,
                    "reason": result.reason,
                    "confidence": result.confidence,
                    "simulated_effects": result.simulated_effects,
                }
                for result in execution_results
            ],
            "execution_summary": {
                "executed": len([r for r in execution_results if r.status == "simulated_executed"]),
                "skipped": len([r for r in execution_results if r.status == "skipped"]),
            },
            "recommendations": [
                {
                    "title": rec.title,
                    "rationale": rec.rationale,
                    "priority": rec.priority,
                    "category": rec.category,
                }
                for rec in recommendations
            ],
        },
    )
    logger.info("Bootstrap complete. Snapshot saved to %s", snapshot_path)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EU4 Assistant + Bot bootstrap CLI")
    parser.add_argument("--mode", choices=[m.value for m in BotMode], default=BotMode.ASSIST.value)
    parser.add_argument("--risk-profile", choices=[p.value for p in RiskProfile], default=RiskProfile.BALANCED.value)
    parser.add_argument("--install-path", type=Path, default=None)
    parser.add_argument("--snapshot-json", type=Path, default=None)
    parser.add_argument("--snapshot-save", type=Path, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    mode = BotMode(args.mode)
    profile = RiskProfile(args.risk_profile)
    raise SystemExit(
        run(
            mode=mode,
            install_path=args.install_path,
            snapshot_json_path=args.snapshot_json,
            snapshot_save_path=args.snapshot_save,
            risk_profile=profile,
        )
    )
