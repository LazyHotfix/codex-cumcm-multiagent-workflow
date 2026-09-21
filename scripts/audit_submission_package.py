"""Audit a CUMCM submission directory for internal artifacts and portability risks."""

from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path
from typing import Any

from _audit_common import (
    DEFAULT_TEXT_SUFFIXES,
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


TOOL = "audit_submission_package"
DEFAULT_FORBIDDEN = [
    ".git",
    ".git/*",
    ".codex",
    ".codex/*",
    "__pycache__",
    "*/__pycache__/*",
    "*.pyc",
    "*.pyo",
    "*.tmp",
    "*.temp",
    "*.bak",
    "*.swp",
    "*.log",
    "reports",
    "reports/*",
    "mvp",
    "mvp/*",
    "result_ai_review",
    "result_ai_review/*",
    "*WORKFLOW_STATE*",
    "*DECISION_LEDGER*",
    "*CHECKPOINT*",
    "*NEXT_PROMPT*",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check a final submission directory for internal state, temporary files, "
            "absolute personal paths and missing required artifacts."
        )
    )
    parser.add_argument("path", help="Submission package directory.")
    parser.add_argument(
        "--forbid",
        action="append",
        default=list(DEFAULT_FORBIDDEN),
        metavar="GLOB",
        help="Relative file/directory glob to reject; may be repeated.",
    )
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="GLOB",
        help="Relative glob allowed even if it matches --forbid; may be repeated.",
    )
    parser.add_argument(
        "--required",
        action="append",
        default=[],
        metavar="GLOB",
        help="Required relative glob; may be repeated.",
    )
    parser.add_argument(
        "--require-extension",
        action="append",
        default=[],
        metavar="EXT",
        help="Require at least one file with extension EXT (for example .pdf).",
    )
    parser.add_argument(
        "--allow-absolute",
        action="append",
        default=[],
        metavar="TEXT",
        help="Absolute-path substring that is allowed in text files; may be repeated.",
    )
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=100 * 1024 * 1024,
        metavar="BYTES",
        help="Reject files larger than this size (default: 100 MiB).",
    )
    add_output_arguments(parser)
    return parser


def _matches(relative: str, patterns: list[str]) -> bool:
    relative = relative.replace("\\", "/")
    name = Path(relative).name
    return any(
        fnmatch.fnmatch(relative, pattern.replace("\\", "/"))
        or fnmatch.fnmatch(name, pattern)
        for pattern in patterns
    )


def main() -> int:
    args = build_parser().parse_args()
    if args.max_file_size < 0:
        return emit_result(TOOL, [], {}, args, error="--max-file-size must be non-negative.")
    root = Path(args.path)
    if not root.exists():
        return emit_result(TOOL, [], {}, args, error=f"Submission path does not exist: {root}")
    if not root.is_dir():
        return emit_result(TOOL, [], {}, args, error=f"Submission path is not a directory: {root}")
    try:
        files = collect_files([root])
    except (AuditRuntimeError, OSError) as exc:
        return emit_result(TOOL, [], {}, args, error=str(exc))

    issues: list[dict[str, Any]] = []
    extension_counts: dict[str, int] = {}
    text_files = 0
    absolute_hits = 0
    for path in files:
        relative = path.relative_to(root).as_posix()
        extension_counts[path.suffix.lower()] = extension_counts.get(path.suffix.lower(), 0) + 1
        if _matches(relative, args.forbid) and not _matches(relative, args.allow):
            issues.append(
                make_issue(
                    "FORBIDDEN_ARTIFACT",
                    "Internal, temporary or generated artifact is present in the submission package.",
                    path=relative,
                )
            )
        try:
            size = path.stat().st_size
        except OSError as exc:
            issues.append(make_issue("STAT_FAILED", str(exc), path=relative))
            continue
        if size > args.max_file_size:
            issues.append(
                make_issue(
                    "FILE_TOO_LARGE",
                    f"File is {size} bytes, above the configured limit {args.max_file_size}.",
                    path=relative,
                )
            )
        if path.suffix.lower() not in DEFAULT_TEXT_SUFFIXES:
            continue
        try:
            text = read_text_file(path)
        except AuditRuntimeError:
            continue
        text_files += 1
        for value in find_absolute_paths(text):
            if any(allowed.casefold() in value.casefold() for allowed in args.allow_absolute):
                continue
            absolute_hits += 1
            offset = text.find(value)
            issues.append(
                make_issue(
                    "ABSOLUTE_PATH",
                    "Personal absolute path found in a submission text file.",
                    path=relative,
                    line=line_number(text, offset),
                    details={"value": value},
                )
            )

    if not files:
        issues.append(make_issue("EMPTY_PACKAGE", "Submission package contains no files."))

    for pattern in args.required:
        if not any(
            fnmatch.fnmatch(path.relative_to(root).as_posix(), pattern.replace("\\", "/"))
            for path in files
        ):
            issues.append(
                make_issue(
                    "REQUIRED_ARTIFACT_MISSING",
                    f"Required artifact pattern {pattern!r} was not found.",
                    details={"pattern": pattern},
                )
            )

    for extension in args.require_extension:
        normalized = extension if extension.startswith(".") else f".{extension}"
        if not any(path.suffix.casefold() == normalized.casefold() for path in files):
            issues.append(
                make_issue(
                    "REQUIRED_EXTENSION_MISSING",
                    f"No file with required extension {normalized!r} was found.",
                    details={"extension": normalized},
                )
            )

    metrics = {
        "files_scanned": len(files),
        "text_files_scanned": text_files,
        "absolute_path_hits": absolute_hits,
        "extensions": extension_counts,
    }
    return emit_result(TOOL, issues, metrics, args)


if __name__ == "__main__":
    run_main(main)
