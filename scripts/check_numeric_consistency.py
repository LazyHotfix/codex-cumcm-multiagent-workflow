"""Find likely numeric inconsistencies across related text and table files."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any

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


TOOL = "check_numeric_consistency"
NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?P<number>[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)(?P<unit>\s*\\?\s*%|\s*(?:万人|人|件|次|天|小时|h|km|m|kg|元|万元|吨|℃|°C|年|月|日)\b)?"
)
PERCENT_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?P<number>[+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*\\?\s*%"
)
LABEL_RE = re.compile(
    r"(?P<label>[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9 _-]{0,38}?)(?:为|是|等于|=|：|:)\s*(?P<value>[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)\s*(?P<unit>\\?\s*%|万人|人|件|次|天|小时|h|km|m|kg|元|万元|吨|℃|°C|年|月|日)?"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit percentages, labelled values and repeated numeric claims. "
            "The tool reports conflicts as review candidates; it does not infer "
            "the intended value."
        )
    )
    parser.add_argument("paths", nargs="+", help="Text file(s) or directories to scan.")
    parser.add_argument(
        "--label",
        action="append",
        default=[],
        metavar="TEXT",
        help="Only inspect labelled values whose label contains TEXT; may repeat.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.0,
        metavar="N",
        help="Absolute tolerance for repeated labelled values (default: 0).",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="GLOB",
        help="Filename glob(s) to skip.",
    )
    add_output_arguments(parser)
    return parser


def parse_number(value: str) -> float:
    return float(value.replace(",", ""))


def normalize_unit(value: str) -> str:
    return re.sub(r"\s+", "", value.replace("\\", "")).casefold()


def _labelled_values(text: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for match in LABEL_RE.finditer(text):
        result.append(
            {
                "label": " ".join(match.group("label").split()).strip(" ：:"),
                "value": parse_number(match.group("value")),
                "unit": normalize_unit(match.group("unit") or ""),
                "line": line_number(text, match.start()),
            }
        )
    return result


def _percent_values(text: str) -> list[dict[str, Any]]:
    return [
        {
            "value": parse_number(match.group("number")),
            "line": line_number(text, match.start()),
        }
        for match in PERCENT_RE.finditer(text)
    ]


def _number_values(text: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for match in NUMBER_RE.finditer(text):
        raw = match.group("number")
        try:
            value = parse_number(raw)
        except ValueError:
            continue
        if not math.isfinite(value):
            continue
        result.append(
            {
                "value": value,
                "unit": normalize_unit(match.group("unit") or ""),
                "line": line_number(text, match.start()),
            }
        )
    return result


def main() -> int:
    args = build_parser().parse_args()
    if args.tolerance < 0:
        return emit_result(
            TOOL,
            [],
            {},
            args,
            error="--tolerance must be non-negative.",
        )
    try:
        files = collect_files(
            args.paths,
            suffixes=DEFAULT_TEXT_SUFFIXES,
            excludes=args.ignore,
        )
    except (AuditRuntimeError, OSError) as exc:
        return emit_result(TOOL, [], {}, args, error=str(exc))

    issues: list[dict[str, Any]] = []
    labelled: dict[tuple[str, str], list[dict[str, Any]]] = {}
    label_units: dict[str, dict[str, list[dict[str, Any]]]] = {}
    percentage_values: list[tuple[Path, float, int]] = []
    numeric_count = 0
    unreadable = 0
    for path in files:
        try:
            text = read_text_file(path)
        except AuditRuntimeError as exc:
            unreadable += 1
            issues.append(make_issue("UNREADABLE_TEXT", str(exc), path=path))
            continue
        numeric_count += len(_number_values(text))
        for item in _labelled_values(text):
            if args.label and not any(value.casefold() in item["label"].casefold() for value in args.label):
                continue
            key = (item["label"].casefold(), item["unit"].casefold())
            labelled.setdefault(key, []).append({**item, "path": path})
            label_units.setdefault(item["label"].casefold(), {}).setdefault(
                item["unit"].casefold(), []
            ).append({**item, "path": path})
        percentage_values.extend(
            (path, item["value"], item["line"]) for item in _percent_values(text)
        )

    for key, values in labelled.items():
        baseline = values[0]["value"]
        for item in values[1:]:
            if abs(item["value"] - baseline) > args.tolerance:
                issues.append(
                    make_issue(
                        "LABEL_VALUE_CONFLICT",
                        f"Label {item['label']!r} has conflicting values {baseline:g} and {item['value']:g}.",
                        path=item["path"],
                        line=item["line"],
                        details={
                            "label": item["label"],
                            "unit": item["unit"],
                            "baseline": baseline,
                            "conflict": item["value"],
                            "other_location": f"{values[0]['path']}:{values[0]['line']}",
                        },
                    )
                )

    for normalized_label, unit_values in label_units.items():
        if len(unit_values) <= 1:
            continue
        units = sorted(unit_values)
        first_item = next(iter(unit_values.values()))[0]
        issues.append(
            make_issue(
                "UNIT_VARIANT",
                f"Label {first_item['label']!r} appears with multiple units: {', '.join(unit or '<none>' for unit in units)}.",
                path=first_item["path"],
                line=first_item["line"],
                severity="warning",
                details={"label": first_item["label"], "units": units},
            )
        )

    if percentage_values:
        for path, value, line in percentage_values:
            if value < 0 or value > 100:
                issues.append(
                    make_issue(
                        "PERCENT_OUT_OF_RANGE",
                        f"Percentage value {value:g}% is outside [0, 100].",
                        path=path,
                        line=line,
                    )
                )

    metrics = {
        "files_scanned": len(files),
        "numeric_tokens": numeric_count,
        "label_groups": len(labelled),
        "labels_with_unit_variants": sum(1 for values in label_units.values() if len(values) > 1),
        "percentages": len(percentage_values),
        "unreadable_files": unreadable,
    }
    return emit_result(TOOL, issues, metrics, args)


if __name__ == "__main__":
    run_main(main)
