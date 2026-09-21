"""Update a G1/G2 gate from an explicit orchestrator decision."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
GENERIC_CONFIRMATIONS = {"继续", "可以", "好的", "继续吧", "ok", "okay", "yes", "go ahead"}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def yaml_scalar(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def append_ledger(path: Path, record: dict[str, object]) -> None:
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = 'schema_version: "1.0"\nledger_type: "CUMCM_DECISION_LEDGER"\ndecisions:\n'

    lines = text.splitlines()
    if not any(line.startswith("decisions:") for line in lines):
        lines.extend(["decisions:"])
    for index, line in enumerate(lines):
        if line.startswith("decisions:") and line.strip() == "decisions: []":
            lines[index] = "decisions:"
    decision_id = str(record.get("decision_id", ""))
    if any(re.match(r"^\s*decision_id:\s*[\"']?" + re.escape(decision_id), line) for line in lines):
        raise ValueError(f"decision_id already exists in ledger: {decision_id}")

    if lines and lines[-1].strip():
        lines.append("")
    lines.append("  -")
    for key, value in record.items():
        lines.append(f"    {key}: {yaml_scalar(value)}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record an explicit G1/G2 decision in state and ledger.")
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--gate", choices=("g1", "g2"), required=True)
    parser.add_argument("--status", choices=("confirmed", "invalidated", "blocked"), required=True)
    parser.add_argument("--decision-id", required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--user-text", required=True)
    parser.add_argument("--confirmed-by", default="user")
    args = parser.parse_args(argv)

    decision_id = args.decision_id.strip()
    user_text = args.user_text.strip()
    if not decision_id:
        print("ERROR: decision id cannot be empty", file=sys.stderr)
        return 2
    if not SHA256_RE.fullmatch(args.packet_sha256.strip()):
        print("ERROR: --packet-sha256 must be a 64-character hexadecimal SHA-256", file=sys.stderr)
        return 2
    if not user_text:
        print("ERROR: --user-text cannot be empty", file=sys.stderr)
        return 2
    if args.status == "confirmed":
        if len(user_text) < 12:
            print("ERROR: confirmation text is too short to establish explicit scope", file=sys.stderr)
            return 2
        if user_text.casefold() in GENERIC_CONFIRMATIONS:
            print("ERROR: generic acknowledgement cannot confirm a gate", file=sys.stderr)
            return 2

    try:
        state = json.loads(args.state.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read state: {exc}", file=sys.stderr)
        return 2

    gate = state.get(args.gate)
    if not isinstance(gate, dict):
        print(f"ERROR: state has no {args.gate} gate object", file=sys.stderr)
        return 2
    current_status = gate.get("status", "NOT_STARTED")
    if args.status == "confirmed" and current_status not in {"NOT_STARTED", "PENDING"}:
        print(f"ERROR: cannot confirm {args.gate} from status {current_status}", file=sys.stderr)
        return 1
    if args.status == "invalidated" and current_status != "CONFIRMED":
        print(f"ERROR: can invalidate only a confirmed {args.gate} gate", file=sys.stderr)
        return 1

    decision_ids = gate.setdefault("decision_ids", [])
    if decision_id in decision_ids:
        print(f"ERROR: decision id already recorded in state: {decision_id}", file=sys.stderr)
        return 1

    gate["status"] = args.status.upper()
    decision_ids.append(decision_id)
    gate["input_hash"] = args.packet_sha256.strip()
    gate["updated_at"] = now()
    if args.status == "confirmed":
        gate["confirmed_at"] = now()
        gate["confirmed_by"] = args.confirmed_by.strip() or "user"
        gate.pop("invalidated_reason", None)
    else:
        gate["invalidated_reason"] = user_text

    state["updated_at"] = now()
    try:
        args.state.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ledger_record = {
            "decision_id": decision_id,
            "decision_type": f"{args.gate}_model_confirmation"
            if args.gate == "g1"
            else "g2_result_confirmation",
            "status": "confirmed" if args.status == "confirmed" else "rejected",
            "gate_status": args.status.upper(),
            "user_text": user_text,
            "run_id": state.get("run_id", ""),
            "input_hash": args.packet_sha256.strip(),
            "created_at": now(),
        }
        append_ledger(args.state.parent / "DECISION_LEDGER.yaml", ledger_record)
    except (OSError, ValueError) as exc:
        print(f"ERROR: cannot persist gate decision: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {"gate": args.gate, "status": gate["status"], "decision_id": decision_id},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
