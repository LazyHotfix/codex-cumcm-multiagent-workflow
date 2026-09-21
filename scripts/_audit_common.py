from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence


EXIT_PASS = 0
EXIT_ISSUES = 1
EXIT_ERROR = 2


DEFAULT_TEXT_SUFFIXES = {
    ".bib",
    ".cfg",
    ".cls",
    ".csv",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".r",
    ".rst",
    ".tex",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}


class AuditRuntimeError(RuntimeError):
    """Raised when an audit cannot be executed reliably."""


def add_output_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--json",
        action="store_true",
        help="Output only the machine-readable JSON result to stdout.",
    )
    group.add_argument(
        "--json-output",
        metavar="PATH",
        help="Write JSON to PATH while keeping the human-readable stdout summary.",
    )


def make_issue(
    code: str,
    message: str,
    *,
    path: str | Path | None = None,
    line: int | None = None,
    severity: str = "error",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
    }
    if path is not None:
        item["path"] = str(path)
    if line is not None:
        item["line"] = line
    if details:
        item["details"] = details
    return item


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, max(offset, 0)) + 1


def read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    if b"\x00" in raw[:8192]:
        raise AuditRuntimeError(f"Binary file cannot be decoded as text: {path}")
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise AuditRuntimeError(f"Unsupported text encoding: {path}")


def matches_any(value: str, patterns: Sequence[str]) -> bool:
    normalized = value.replace("\\", "/")
    name = Path(normalized).name
    return any(
        fnmatch.fnmatch(normalized, pattern.replace("\\", "/"))
        or fnmatch.fnmatch(name, pattern)
        for pattern in patterns
    )


def collect_files(
    paths: Sequence[str | Path],
    *,
    suffixes: set[str] | None = None,
    includes: Sequence[str] = (),
    excludes: Sequence[str] = (),
) -> list[Path]:
    suffixes = {suffix.lower() for suffix in suffixes} if suffixes else None
    found: dict[str, Path] = {}
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            raise AuditRuntimeError(f"Input path does not exist: {path}")
        candidates: Iterable[Path]
        if path.is_file():
            candidates = (path,)
            root = path.parent
        elif path.is_dir():
            candidates = path.rglob("*")
            root = path
        else:
            raise AuditRuntimeError(f"Unsupported input path type: {path}")

        for candidate in candidates:
            if not candidate.is_file():
                continue
            try:
                relative = candidate.relative_to(root).as_posix()
            except ValueError:
                relative = candidate.name
            if excludes and matches_any(relative, excludes):
                continue
            if includes and not matches_any(relative, includes):
                continue
            if suffixes is not None and candidate.suffix.lower() not in suffixes:
                continue
            key = str(candidate.resolve()).casefold()
            found[key] = candidate
    return sorted(found.values(), key=lambda item: str(item).casefold())


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


WINDOWS_ABSOLUTE_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/](?:[^\s\"'<>|]+[\\/]?)+|\\\\[^\\\s]+\\[^\s\"'<>|]+)"
)
WINDOWS_QUOTED_RE = re.compile(
    r"(?P<quote>[\"'])(?P<path>(?:[A-Za-z]:[\\/]|\\\\)[^\"'\r\n]+)(?P=quote)"
)
POSIX_PERSONAL_RE = re.compile(
    r"(?<![A-Za-z0-9])/(?:Users|home|root|mnt|tmp|var/tmp)/[^\s\"'<>|]+"
)


def find_absolute_paths(text: str) -> list[str]:
    values: list[str] = []
    for match in WINDOWS_ABSOLUTE_RE.finditer(text):
        values.append(match.group(0))
    for match in WINDOWS_QUOTED_RE.finditer(text):
        values.append(match.group("path"))
    for match in POSIX_PERSONAL_RE.finditer(text):
        values.append(match.group(0))
    # A quoted path is also matched by the unquoted expression in some cases.
    return list(dict.fromkeys(values))


def emit_result(
    tool: str,
    issues: list[dict[str, Any]],
    metrics: dict[str, Any],
    args: argparse.Namespace,
    *,
    error: str | None = None,
) -> int:
    if error is not None:
        status = "error"
        exit_code = EXIT_ERROR
        summary = f"{tool} could not complete: {error}"
    elif issues:
        status = "issues"
        exit_code = EXIT_ISSUES
        summary = f"{tool} found {len(issues)} audit issue(s)."
    else:
        status = "pass"
        exit_code = EXIT_PASS
        summary = f"{tool} passed with no audit issues."

    payload: dict[str, Any] = {
        "tool": tool,
        "status": status,
        "exit_code": exit_code,
        "summary": summary,
        "metrics": metrics,
        "issues": issues,
    }
    if error is not None:
        payload["error"] = error

    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if getattr(args, "json", False):
        print(serialized)
    else:
        marker = {"pass": "PASS", "issues": "FAIL", "error": "ERROR"}[status]
        print(f"[{marker}] {summary}")
        if metrics:
            metrics_text = ", ".join(f"{key}={value}" for key, value in metrics.items())
            print(f"Summary: {metrics_text}")
        for item in issues:
            location = ""
            if item.get("path"):
                location = str(item["path"])
                if item.get("line") is not None:
                    location += f":{item['line']}"
                location += ": "
            print(
                f"- {item.get('severity', 'error').upper()} {item['code']}: "
                f"{location}{item['message']}"
            )

    json_output = getattr(args, "json_output", None)
    if json_output:
        try:
            output_path = Path(json_output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(serialized + "\n", encoding="utf-8")
        except OSError as exc:
            if not getattr(args, "json", False):
                print(f"[ERROR] Could not write JSON output: {exc}", file=sys.stderr)
            return EXIT_ERROR
    return exit_code


def run_main(main_function: Any) -> None:
    try:
        code = int(main_function())
    except BrokenPipeError:
        # A consumer such as `head` may close stdout after reading enough output.
        code = EXIT_PASS
    except KeyboardInterrupt:
        print("[ERROR] Audit interrupted by user.", file=sys.stderr)
        code = EXIT_ERROR
    except Exception as exc:  # Defensive CLI boundary.
        print(f"[ERROR] Unexpected audit failure: {exc}", file=sys.stderr)
        code = EXIT_ERROR
    raise SystemExit(code)
