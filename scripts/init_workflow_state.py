"""Initialize a CUMCM project workflow state and its control-plane ledgers."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_registry(path: Path) -> dict[str, object]:
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read phase registry: {exc}") from exc
    phases = registry.get("phases")
    entry = registry.get("entry_phase")
    if not isinstance(registry.get("workflow_id"), str):
        raise ValueError("phase registry workflow_id is missing")
    if not isinstance(phases, list) or not phases:
        raise ValueError("phase registry phases must be a non-empty list")
    phase_ids = {item.get("id") for item in phases if isinstance(item, dict)}
    if entry not in phase_ids:
        raise ValueError(f"entry_phase is not registered: {entry!r}")
    return registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize a CUMCM local workflow state.")
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--project-id", required=True)
    parser.add_argument(
        "--registry",
        type=Path,
        help="Phase registry; defaults to <project-root>/shared/PHASE_REGISTRY.json.",
    )
    parser.add_argument("--force", action="store_true", help="replace an existing state file")
    args = parser.parse_args(argv)

    root = args.project_root.resolve()
    if not root.is_dir():
        print(f"ERROR: project root is not a directory: {root}", file=sys.stderr)
        return 2
    if not args.project_id.strip():
        print("ERROR: --project-id cannot be empty", file=sys.stderr)
        return 2

    registry_path = (args.registry or (root / "shared" / "PHASE_REGISTRY.json")).resolve()
    try:
        registry = read_registry(registry_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    reports = root / "reports"
    state_path = reports / "WORKFLOW_STATE.json"
    if state_path.exists() and not args.force:
        print(f"ERROR: state exists: {state_path}", file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_id = f"run-{stamp}-{uuid.uuid4().hex[:8]}"
    state = {
        "schema_version": "1.0",
        "workflow_id": registry["workflow_id"],
        "project_id": args.project_id.strip(),
        "current_phase": registry["entry_phase"],
        "stage_status": "NOT_STARTED",
        "phase_result": None,
        "run_id": run_id,
        "problem_scope": [],
        "g1": {"status": "NOT_STARTED", "decision_ids": [], "input_hash": ""},
        "g2": {"status": "NOT_STARTED", "decision_ids": [], "input_hash": ""},
        "canonical": {},
        "assets": [],
        "pending_decisions": [],
        "blocking_issues": [],
        "phase_history": [],
        "last_verified_hash": "",
        "delivery_status": "NOT_READY",
        "updated_at": now(),
    }

    reports.mkdir(parents=True, exist_ok=True)
    (reports / "locks").mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ledger = reports / "DECISION_LEDGER.yaml"
    if args.force or not ledger.exists():
        ledger.write_text(
            'schema_version: "1.0"\n'
            'ledger_type: "CUMCM_DECISION_LEDGER"\n'
            "decisions:\n",
            encoding="utf-8",
        )

    invalidation_log = reports / "INVALIDATION_LOG.csv"
    if args.force or not invalidation_log.exists():
        invalidation_log.write_text(
            "source_asset,affected_asset,reason,created_at,run_id,rerun_phase\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "state": str(state_path),
                "registry": str(registry_path),
                "workflow_id": registry["workflow_id"],
                "current_phase": registry["entry_phase"],
                "run_id": run_id,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

