"""Validate local workflow state and phase registry without third-party packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


STAGE_STATUSES = {"NOT_STARTED", "RUNNING", "WAITING_USER", "BLOCKED", "PASS", "FAIL"}
GATE_STATUSES = {"NOT_STARTED", "PENDING", "CONFIRMED", "INVALIDATED", "BLOCKED"}
DELIVERY_STATUSES = {"NOT_READY", "PARTIAL", "VERIFY_PASS", "FULL_PASS", "RELEASE_BLOCKED"}
ASSET_STATUSES = {"planned", "generated", "needs_confirmation", "embedded", "verified", "obsolete", "blocked"}
REQUIRED = {
    "schema_version",
    "workflow_id",
    "project_id",
    "current_phase",
    "stage_status",
    "run_id",
    "problem_scope",
    "g1",
    "g2",
    "canonical",
    "assets",
    "pending_decisions",
    "blocking_issues",
    "phase_history",
    "delivery_status",
}
RUN_ID_RE = re.compile(r"^run-[A-Za-z0-9._-]+$")


def load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate WORKFLOW_STATE.json and phase registry.")
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    try:
        state = load_json(args.state, "state")
        registry = load_json(args.registry, "registry")
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    issues: list[str] = []
    if not isinstance(state, dict):
        issues.append("state root must be an object")
        state = {}
    if not isinstance(registry, dict):
        issues.append("registry root must be an object")
        registry = {}

    missing = sorted(REQUIRED - set(state))
    issues.extend(f"missing state field: {name}" for name in missing)

    workflow_id = registry.get("workflow_id")
    if not isinstance(workflow_id, str) or not workflow_id:
        issues.append("registry workflow_id must be a non-empty string")
    elif state.get("workflow_id") != workflow_id:
        issues.append("workflow_id differs from phase registry")

    phases = registry.get("phases")
    if not isinstance(phases, list) or not phases:
        issues.append("registry phases must be a non-empty list")
        phases = []
    phase_ids: list[str] = []
    phase_by_id: dict[str, dict[str, Any]] = {}
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            issues.append(f"registry phase[{index}] must be an object")
            continue
        phase_id = phase.get("id")
        owner = phase.get("owner")
        if not isinstance(phase_id, str) or not phase_id:
            issues.append(f"registry phase[{index}] has invalid id")
            continue
        if phase_id in phase_by_id:
            issues.append(f"duplicate phase id: {phase_id}")
        phase_ids.append(phase_id)
        phase_by_id[phase_id] = phase
        if not isinstance(owner, str) or not owner:
            issues.append(f"registry phase {phase_id} has no owner")
        next_phase = phase.get("next")
        if next_phase is not None and next_phase not in {p.get("id") for p in phases if isinstance(p, dict)}:
            issues.append(f"registry phase {phase_id} points to unknown next phase: {next_phase!r}")

    entry_phase = registry.get("entry_phase")
    if entry_phase not in phase_by_id:
        issues.append(f"registry entry_phase is not registered: {entry_phase!r}")
    current_phase = state.get("current_phase")
    if current_phase not in phase_by_id:
        issues.append(f"current_phase not in registry: {current_phase!r}")

    if state.get("stage_status") not in STAGE_STATUSES:
        issues.append(f"invalid stage_status: {state.get('stage_status')!r}")
    if state.get("delivery_status") not in DELIVERY_STATUSES:
        issues.append(f"invalid delivery_status: {state.get('delivery_status')!r}")
    if not isinstance(state.get("run_id"), str) or not RUN_ID_RE.fullmatch(state.get("run_id", "")):
        issues.append("run_id must match ^run-[A-Za-z0-9._-]+$")

    for gate_name in ("g1", "g2"):
        gate = state.get(gate_name, {})
        if not isinstance(gate, dict):
            issues.append(f"{gate_name} must be an object")
            continue
        if gate.get("status") not in GATE_STATUSES:
            issues.append(f"invalid {gate_name}.status: {gate.get('status')!r}")
        if not isinstance(gate.get("decision_ids", []), list):
            issues.append(f"{gate_name}.decision_ids must be a list")
        if "input_hash" in gate and not isinstance(gate["input_hash"], str):
            issues.append(f"{gate_name}.input_hash must be a string")
        if gate.get("status") == "CONFIRMED" and not gate.get("decision_ids"):
            issues.append(f"{gate_name} is confirmed without a decision id")

    assets = state.get("assets", [])
    if not isinstance(assets, list):
        issues.append("assets must be a list")
        assets = []
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            issues.append(f"asset[{index}] must be an object")
            continue
        required = ("asset_id", "path", "status", "owner", "source_phase")
        if not all(key in asset for key in required):
            issues.append(f"asset[{index}] missing one of {required}")
        if asset.get("status") not in ASSET_STATUSES:
            issues.append(f"asset[{index}] has invalid status: {asset.get('status')!r}")
        if asset.get("source_phase") not in phase_by_id:
            issues.append(f"asset[{index}] source_phase is not registered: {asset.get('source_phase')!r}")

    canonical = state.get("canonical", {})
    if not isinstance(canonical, dict):
        issues.append("canonical must be an object")
    else:
        for key, item in canonical.items():
            if not isinstance(item, dict):
                issues.append(f"canonical[{key}] must be an object")
                continue
            if not all(field in item for field in ("path", "owner", "status")):
                issues.append(f"canonical[{key}] missing path, owner or status")
            if item.get("status") not in ASSET_STATUSES:
                issues.append(f"canonical[{key}] has invalid status: {item.get('status')!r}")

    history = state.get("phase_history", [])
    if not isinstance(history, list):
        issues.append("phase_history must be a list")
        history = []
    for index, item in enumerate(history):
        if not isinstance(item, dict):
            issues.append(f"phase_history[{index}] must be an object")
            continue
        for field in ("phase", "status", "run_id", "started_at"):
            if field not in item:
                issues.append(f"phase_history[{index}] missing {field}")
        if item.get("phase") not in phase_by_id:
            issues.append(f"phase_history[{index}] phase is not registered: {item.get('phase')!r}")
        if isinstance(item.get("run_id"), str) and not RUN_ID_RE.fullmatch(item["run_id"]):
            issues.append(f"phase_history[{index}] has invalid run_id")

    parallel_windows = registry.get("parallel_windows", [])
    if not isinstance(parallel_windows, list):
        issues.append("registry parallel_windows must be a list")
    else:
        for index, window in enumerate(parallel_windows):
            if not isinstance(window, list) or len(window) != 2:
                issues.append(f"parallel_windows[{index}] must contain exactly two phase ids")
                continue
            for phase_id in window:
                if phase_id not in phase_by_id and not (
                    isinstance(phase_id, str) and ":" in phase_id and phase_id.split(":", 1)[0] in phase_by_id
                ):
                    issues.append(f"parallel_windows[{index}] references unknown phase: {phase_id!r}")

    result = {
        "status": "PASS" if not issues else "ISSUES",
        "issues": issues,
        "state": str(args.state),
        "registry": str(args.registry),
        "phase_count": len(phase_by_id),
    }
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']}: {args.state}")
        for issue in issues:
            print(f"- {issue}")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())

