"""Check that user-locked text is present and superseded text is absent."""

from __future__ import annotations

import argparse
from pathlib import Path

from _audit_common import (
    DEFAULT_TEXT_SUFFIXES,
    AuditRuntimeError,
    add_output_arguments,
    collect_files,
    emit_result,
    line_number,
    make_issue,
    read_text_file,
    run_main,
)


TOOL = "check_locked_text"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that required locked wording appears and forbidden legacy "
            "wording no longer appears in a text tree."
        )
    )
    parser.add_argument("paths", nargs="+", help="Text file(s) or directories to scan.")
    parser.add_argument(
        "--required",
        action="append",
        default=[],
        metavar="TEXT",
        help="Text that must occur at least once; may be repeated.",
    )
    parser.add_argument(
        "--forbidden",
        action="append",
        default=[],
        metavar="TEXT",
        help="Text that must not occur; may be repeated.",
    )
    parser.add_argument(
        "--required-file",
        action="append",
        default=[],
        metavar="PATH",
        help="Read one required phrase from each file (trailing newlines are removed).",
    )
    parser.add_argument(
        "--forbidden-file",
        action="append",
        default=[],
        metavar="PATH",
        help="Read one forbidden phrase from each file (trailing newlines are removed).",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="GLOB",
        help="Additional filename glob(s), for example '*.locked'.",
    )
    parser.add_argument(
        "--ignore-case",
        action="store_true",
        help="Use case-insensitive matching.",
    )
    add_output_arguments(parser)
    return parser


def _load_phrases(
    inline: list[str], files: list[str], kind: str, issues: list[dict[str, object]]
) -> list[str]:
    phrases = list(inline)
    for raw_path in files:
        path = Path(raw_path)
        if not path.is_file():
            raise AuditRuntimeError(f"{kind} phrase file does not exist: {path}")
        try:
            value = read_text_file(path).rstrip("\r\n")
        except AuditRuntimeError as exc:
            raise AuditRuntimeError(str(exc)) from exc
        if not value:
            issues.append(
                make_issue(
                    "EMPTY_PHRASE",
                    f"{kind} phrase file is empty.",
                    path=path,
                )
            )
        phrases.append(value)
    for index, phrase in enumerate(phrases):
        if not phrase:
            issues.append(
                make_issue(
                    "EMPTY_PHRASE",
                    f"{kind} phrase at index {index} is empty.",
                )
            )
    return phrases


def main() -> int:
    args = build_parser().parse_args()
    issues: list[dict[str, object]] = []
    try:
        required = _load_phrases(args.required, args.required_file, "Required", issues)
        forbidden = _load_phrases(args.forbidden, args.forbidden_file, "Forbidden", issues)
        if not required and not forbidden:
            return emit_result(
                TOOL,
                issues,
                {},
                args,
                error="At least one --required, --forbidden, --required-file or --forbidden-file is required.",
            )
        if issues:
            return emit_result(TOOL, issues, {}, args)

        nonstandard_file = any(
            Path(raw).is_file() and Path(raw).suffix.lower() not in DEFAULT_TEXT_SUFFIXES
            for raw in args.paths
        )
        suffixes = None if args.include or nonstandard_file else DEFAULT_TEXT_SUFFIXES
        files = collect_files(
            args.paths,
            suffixes=suffixes,
            includes=args.include,
        )
    except (AuditRuntimeError, OSError) as exc:
        return emit_result(TOOL, issues, {}, args, error=str(exc))

    if not files:
        issues.append(
            make_issue(
                "NO_TEXT_FILES",
                "No scannable text files were found.",
            )
        )

    folded_required = [value.casefold() if args.ignore_case else value for value in required]
    folded_forbidden = [value.casefold() if args.ignore_case else value for value in forbidden]
    occurrences: dict[str, int] = {phrase: 0 for phrase in required + forbidden}

    for path in files:
        try:
            text = read_text_file(path)
        except AuditRuntimeError as exc:
            issues.append(make_issue("UNREADABLE_TEXT", str(exc), path=path))
            continue
        haystack = text.casefold() if args.ignore_case else text

        for original, phrase in zip(required, folded_required):
            count = haystack.count(phrase)
            if count:
                occurrences[original] = occurrences.get(original, 0) + count

        for original, phrase in zip(forbidden, folded_forbidden):
            count = haystack.count(phrase)
            if not count:
                continue
            occurrences[original] = occurrences.get(original, 0) + count
            offset = haystack.find(phrase)
            issues.append(
                make_issue(
                    "FORBIDDEN_TEXT_FOUND",
                    f"Forbidden text occurs {count} time(s).",
                    path=path,
                    line=line_number(text, offset),
                    details={"text": original, "occurrences": count},
                )
            )

    for original, phrase in zip(required, folded_required):
        if occurrences.get(original, 0) == 0:
            issues.append(
                make_issue(
                    "REQUIRED_TEXT_MISSING",
                    "Required locked text was not found.",
                    details={"text": original},
                )
            )

    metrics = {
        "files_scanned": len(files),
        "required_phrases": len(required),
        "forbidden_phrases": len(forbidden),
    }
    return emit_result(TOOL, issues, metrics, args)


if __name__ == "__main__":
    run_main(main)
