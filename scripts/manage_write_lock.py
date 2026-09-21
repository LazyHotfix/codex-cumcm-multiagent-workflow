"""Acquire or release an owner-aware canonical file lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def lock_file(lock_dir: Path, relative_path: str) -> Path:
    safe = relative_path.replace("\\", "__").replace("/", "__").replace(":", "")
    return lock_dir / f"{safe}.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage reports/locks/*.json for canonical files.")
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--path", required=True, help="canonical path relative to project root")
    parser.add_argument("--owner-agent", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--lock-id")
    parser.add_argument("--expected-input-sha256")
    parser.add_argument("action", choices=("acquire", "release"))
    args = parser.parse_args(argv)

    root = args.project_root.resolve()
    if not root.is_dir():
        print(f"ERROR: project root is not a directory: {root}", file=sys.stderr)
        return 2
    target = (root / args.path).resolve()
    try:
        relative_path = target.relative_to(root).as_posix()
    except ValueError:
        print("ERROR: path must remain inside project root", file=sys.stderr)
        return 2
    if not relative_path or relative_path == ".":
        print("ERROR: canonical path cannot be the project root", file=sys.stderr)
        return 2

    lock_dir = root / "reports" / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_file(lock_dir, relative_path)
    lock_id = args.lock_id or ("lock-" + uuid.uuid4().hex[:12])
    current_input = sha256(target) if target.is_file() else "MISSING"

    if args.action == "acquire":
        if args.expected_input_sha256 and args.expected_input_sha256 != current_input:
            print(
                json.dumps(
                    {
                        "status": "INPUT_CHANGED",
                        "expected": args.expected_input_sha256,
                        "actual": current_input,
                    },
                    ensure_ascii=False,
                )
            )
            return 1
        if lock_path.exists():
            try:
                current = json.loads(lock_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                print(f"ERROR: unreadable existing lock: {exc}", file=sys.stderr)
                return 2
            if current.get("status") == "HELD":
                print(json.dumps({"status": "CONFLICT", "lock": current}, ensure_ascii=False))
                return 1
        record = {
            "lock_id": lock_id,
            "path": relative_path,
            "owner_agent": args.owner_agent,
            "run_id": args.run_id,
            "reason": args.reason,
            "input_sha256": current_input,
            "created_at": now(),
            "status": "HELD",
        }
        lock_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(record, ensure_ascii=False))
        return 0

    if not lock_path.exists():
        print("ERROR: lock does not exist", file=sys.stderr)
        return 2
    try:
        record = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read lock: {exc}", file=sys.stderr)
        return 2
    if record.get("status") != "HELD":
        print(f"ERROR: lock is not held: {record.get('status')}", file=sys.stderr)
        return 1
    if args.lock_id and record.get("lock_id") != args.lock_id:
        print("ERROR: lock id mismatch", file=sys.stderr)
        return 1
    if record.get("owner_agent") != args.owner_agent or record.get("run_id") != args.run_id:
        print("ERROR: owner or run_id mismatch", file=sys.stderr)
        return 1

    record["output_sha256"] = sha256(target) if target.is_file() else "MISSING"
    record["released_at"] = now()
    record["status"] = "RELEASED"
    lock_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

