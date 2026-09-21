"""Record dependency invalidation in state and the CSV audit log."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def append_row(path: Path, row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_asset", "affected_asset", "reason", "created_at", "run_id", "rerun_phase"],
        )
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Propagate a canonical asset change through local workflow state.")
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--source-asset", required=True)
    parser.add_argument("--affected-asset", action="append", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--rerun-phase", required=True)
    parser.add_argument("--invalidate-gate", action="append", choices=("g1", "g2"))
    args = parser.parse_args(argv)

    try:
        state = json.loads(args.state.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read state: {exc}", file=sys.stderr)
        return 2
    if not isinstance(state, dict):
        print("ERROR: state root must be an object", file=sys.stderr)
        return 2

    timestamp = now()
    run_id = str(state.get("run_id", ""))
    for affected in args.affected_asset:
        for asset in state.get("assets", []):
            if isinstance(asset, dict) and asset.get("asset_id") == affected:
                asset["status"] = "obsolete"
                asset["invalidated_at"] = timestamp
                asset["invalidated_reason"] = args.reason
        canonical = state.get("canonical", {}).get(affected)
        if isinstance(canonical, dict):
            canonical["status"] = "obsolete"
            canonical["updated_at"] = timestamp
        append_row(
            args.state.parent / "INVALIDATION_LOG.csv",
            {
                "source_asset": args.source_asset,
                "affected_asset": affected,
                "reason": args.reason,
                "created_at": timestamp,
                "run_id": run_id,
                "rerun_phase": args.rerun_phase,
            },
        )

    for gate_name in args.invalidate_gate or []:
        gate = state.get(gate_name)
        if isinstance(gate, dict) and gate.get("status") == "CONFIRMED":
            gate["status"] = "INVALIDATED"
            gate["invalidated_reason"] = args.reason
            gate["updated_at"] = timestamp

    state["last_verified_hash"] = ""
    state["updated_at"] = timestamp
    args.state.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "INVALIDATED",
                "source_asset": args.source_asset,
                "affected_assets": args.affected_asset,
                "rerun_phase": args.rerun_phase,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

