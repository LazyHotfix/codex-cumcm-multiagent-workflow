"""Audit a Python code tree for syntax, runnable entry points and hard-coded paths."""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
import tokenize
from pathlib import Path
from typing import Any

from _audit_common import (
    AuditRuntimeError,
    add_output_arguments,
    collect_files,
    emit_result,
    find_absolute_paths,
    line_number,
    make_issue,
    read_text_file,
    run_main,
)


TOOL = "audit_code_closure"
PY_SUFFIXES = {".py", ".pyw"}
DEFAULT_ENTRY_NAMES = {"run_all.py", "main.py", "cli.py", "run.py"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check Python syntax, discover or validate an execution entry point, "
            "and report hard-coded absolute personal paths."
        )
    )
    parser.add_argument("path", help="Python project directory or file.")
    parser.add_argument(
        "--entry",
        action="append",
        default=[],
        metavar="PATH",
        help="Entry file to require; may be repeated. Without this, common names are discovered.",
    )
    parser.add_argument(
        "--allow-absolute",
        action="append",
        default=[],
        metavar="TEXT",
        help="Absolute-path substring that is allowed; may be repeated.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[".git", ".venv", "venv", "__pycache__", "build", "dist"],
        metavar="GLOB",
        help="File/directory glob(s) to exclude.",
    )
    parser.add_argument(
        "--compileall",
        action="store_true",
        help="Also run Python's compileall after AST checks (optional extra check).",
    )
    add_output_arguments(parser)
    return parser


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _entry_paths(raw_entries: list[str], root: Path, files: list[Path]) -> list[Path]:
    if raw_entries:
        entries = []
        for raw in raw_entries:
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = root / candidate
            entries.append(candidate)
        return entries
    return [path for path in files if path.name.casefold() in DEFAULT_ENTRY_NAMES]


def _compile_with_tokenize(path: Path) -> str | None:
    try:
        with tokenize.open(path) as handle:
            source = handle.read()
        ast.parse(source, filename=str(path))
        return None
    except (SyntaxError, UnicodeError, OSError) as exc:
        return str(exc)


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.path)
    if not root.exists():
        return emit_result(TOOL, [], {}, args, error=f"Input path does not exist: {root}")
    if root.is_file() and root.suffix.lower() not in PY_SUFFIXES:
        return emit_result(TOOL, [], {}, args, error=f"Input file is not Python: {root}")
    scan_root = root if root.is_dir() else root.parent
    try:
        files = collect_files(
            [root],
            suffixes=PY_SUFFIXES,
            excludes=args.exclude,
        )
    except (AuditRuntimeError, OSError) as exc:
        return emit_result(TOOL, [], {}, args, error=str(exc))

    issues: list[dict[str, Any]] = []
    syntax_errors = 0
    absolute_hits = 0
    for path in files:
        syntax_error = _compile_with_tokenize(path)
        if syntax_error:
            syntax_errors += 1
            issues.append(make_issue("PYTHON_SYNTAX_ERROR", syntax_error, path=path))
        try:
            text = read_text_file(path)
        except AuditRuntimeError as exc:
            issues.append(make_issue("UNREADABLE_SOURCE", str(exc), path=path))
            continue
        for value in find_absolute_paths(text):
            if any(allowed.casefold() in value.casefold() for allowed in args.allow_absolute):
                continue
            absolute_hits += 1
            offset = text.find(value)
            issues.append(
                make_issue(
                    "ABSOLUTE_PATH",
                    "Hard-coded absolute path found; use a project-relative or configurable path.",
                    path=path,
                    line=line_number(text, offset),
                    details={"value": value},
                )
            )

    entries = _entry_paths(args.entry, scan_root, files)
    if not entries:
        issues.append(
            make_issue(
                "MISSING_ENTRY_POINT",
                "No entry point found. Provide --entry or add run_all.py, main.py, cli.py or run.py.",
            )
        )
    entry_count = 0
    for entry in entries:
        if not entry.is_file():
            issues.append(make_issue("ENTRY_NOT_FOUND", "Required entry file does not exist.", path=entry))
            continue
        if entry.suffix.lower() not in PY_SUFFIXES:
            issues.append(make_issue("ENTRY_NOT_PYTHON", "Entry file is not Python.", path=entry))
            continue
        entry_count += 1
        if _compile_with_tokenize(entry):
            continue

    if args.compileall and files:
        # compileall is intentionally quiet; AST diagnostics above identify each file.
        import compileall

        if not compileall.compile_dir(str(scan_root), quiet=1, force=False):
            issues.append(
                make_issue(
                    "COMPILEALL_FAILED",
                    "Python compileall reported a failure.",
                    path=scan_root,
                )
            )

    metrics = {
        "python_files": len(files),
        "syntax_errors": syntax_errors,
        "absolute_path_hits": absolute_hits,
        "entry_points": entry_count,
        "python_executable": sys.executable,
        "compileall_requested": bool(args.compileall),
        "shutil_which_python": shutil.which("python") or "",
    }
    return emit_result(TOOL, issues, metrics, args)


if __name__ == "__main__":
    run_main(main)
