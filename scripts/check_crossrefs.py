"""Check LaTeX and Markdown cross-reference declarations and uses."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from _audit_common import (
    AuditRuntimeError,
    add_output_arguments,
    collect_files,
    emit_result,
    line_number,
    make_issue,
    read_text_file,
    run_main,
)


TOOL = "check_crossrefs"
LATEX_SUFFIXES = {".tex", ".cls", ".sty", ".bib"}
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdown"}
LABEL_RE = re.compile(r"\\label\s*\{([^{}]+)\}")
REF_RE = re.compile(
    r"\\(?:ref|pageref|autoref|cref|Cref|eqref|nameref|vref|cpageref|crefrange)\*?\s*\{([^{}]+)\}"
)
CITE_RE = re.compile(r"\\(?:cite|citep|citet|parencite|textcite)(?:\w*)?\s*(?:\[[^\]]*\]\s*)*\{([^{}]+)\}")
HYPERREF_RE = re.compile(r"\\hyperref\s*\[([^\]]+)\]")
BIB_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)", re.IGNORECASE)
MD_HEADING_RE = re.compile(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(#([^)]+)\)")
MD_HTML_ANCHOR_RE = re.compile(r"<a\s+[^>]*id=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check duplicate and undefined LaTeX/Markdown labels and references."
    )
    parser.add_argument("paths", nargs="+", help="LaTeX, Markdown or bibliography paths.")
    parser.add_argument(
        "--allow-label",
        action="append",
        default=[],
        metavar="LABEL",
        help="Label allowed to remain unused or unresolved; may be repeated.",
    )
    parser.add_argument(
        "--allow-reference",
        action="append",
        default=[],
        metavar="LABEL",
        help="Reference allowed to remain unresolved; may be repeated.",
    )
    parser.add_argument(
        "--no-unused",
        action="store_true",
        help="Do not report declared labels that are never referenced.",
    )
    parser.add_argument(
        "--no-citations",
        action="store_true",
        help="Skip citation-key checks between LaTeX and .bib files.",
    )
    add_output_arguments(parser)
    return parser


def strip_latex_comments(text: str) -> str:
    lines = []
    for line in text.splitlines(keepends=True):
        escaped = False
        cut = len(line)
        for index, char in enumerate(line):
            if char == "%" and not escaped:
                cut = index
                break
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
        lines.append(line[:cut])
    return "".join(lines)


def heading_slug(heading: str) -> str:
    heading = re.sub(r"<[^>]+>", "", heading).strip().casefold()
    heading = re.sub(r"[^\w\u4e00-\u9fff -]", "", heading, flags=re.UNICODE)
    return re.sub(r"\s+", "-", heading)


def main() -> int:
    args = build_parser().parse_args()
    try:
        files = collect_files(args.paths)
    except (AuditRuntimeError, OSError) as exc:
        return emit_result(TOOL, [], {}, args, error=str(exc))

    issues: list[dict[str, Any]] = []
    labels: dict[str, list[dict[str, Any]]] = {}
    references: list[dict[str, Any]] = []
    citation_uses: list[dict[str, Any]] = []
    bib_keys: dict[str, list[dict[str, Any]]] = {}
    scanned = 0
    for path in files:
        suffix = path.suffix.lower()
        if suffix not in LATEX_SUFFIXES and suffix not in MARKDOWN_SUFFIXES:
            continue
        try:
            text = read_text_file(path)
        except AuditRuntimeError as exc:
            issues.append(make_issue("UNREADABLE_TEXT", str(exc), path=path))
            continue
        scanned += 1
        if suffix == ".bib" and not args.no_citations:
            for match in BIB_RE.finditer(text):
                key = match.group(1).strip()
                bib_keys.setdefault(key, []).append(
                    {"path": path, "line": line_number(text, match.start())}
                )
        elif suffix in LATEX_SUFFIXES:
            active = strip_latex_comments(text)
            for match in LABEL_RE.finditer(active):
                label = match.group(1).strip()
                labels.setdefault(label, []).append(
                    {"path": path, "line": line_number(text, match.start()), "kind": "latex"}
                )
            for match in REF_RE.finditer(active):
                for label in match.group(1).split(","):
                    label = label.strip()
                    if label:
                        references.append(
                            {"label": label, "path": path, "line": line_number(text, match.start())}
                        )
            for match in HYPERREF_RE.finditer(active):
                references.append(
                    {
                        "label": match.group(1).strip(),
                        "path": path,
                        "line": line_number(text, match.start()),
                    }
                )
            if not args.no_citations:
                for match in CITE_RE.finditer(active):
                    for key in match.group(1).split(","):
                        key = key.strip()
                        if key:
                            citation_uses.append(
                                {"key": key, "path": path, "line": line_number(text, match.start())}
                            )
        elif suffix in MARKDOWN_SUFFIXES:
            for match in MD_HTML_ANCHOR_RE.finditer(text):
                labels.setdefault(match.group(1).strip(), []).append(
                    {"path": path, "line": line_number(text, match.start()), "kind": "markdown"}
                )
            for match in MD_HEADING_RE.finditer(text):
                slug = heading_slug(match.group(1))
                if slug:
                    labels.setdefault(slug, []).append(
                        {"path": path, "line": line_number(text, match.start()), "kind": "markdown-heading"}
                    )
            for match in MD_LINK_RE.finditer(text):
                references.append(
                    {"label": match.group(1).strip(), "path": path, "line": line_number(text, match.start())}
                )

    for label, locations in labels.items():
        if len(locations) > 1 and label not in args.allow_label:
            first = locations[0]
            issues.append(
                make_issue(
                    "DUPLICATE_LABEL",
                    f"Label {label!r} is declared {len(locations)} times.",
                    path=first["path"],
                    line=first["line"],
                    details={
                        "label": label,
                        "locations": [f"{item['path']}:{item['line']}" for item in locations],
                    },
                )
            )

    used_labels = {item["label"] for item in references}
    for item in references:
        label = item["label"]
        if label in labels or label in args.allow_reference or label in args.allow_label:
            continue
        issues.append(
            make_issue(
                "UNDEFINED_REFERENCE",
                f"Reference {label!r} has no matching declaration.",
                path=item["path"],
                line=item["line"],
                details={"label": label},
            )
        )

    if not args.no_unused:
        for label, locations in labels.items():
            if label in used_labels or label in args.allow_label:
                continue
            # Bibliography labels and headings are often valid navigation targets.
            if any(item["kind"] == "markdown-heading" for item in locations):
                continue
            first = locations[0]
            issues.append(
                make_issue(
                    "UNUSED_LABEL",
                    f"Label {label!r} is declared but never referenced.",
                    path=first["path"],
                    line=first["line"],
                    severity="warning",
                    details={"label": label},
                )
            )

    if not args.no_citations:
        for key, locations in bib_keys.items():
            if len(locations) > 1:
                first = locations[0]
                issues.append(
                    make_issue(
                        "DUPLICATE_BIB_KEY",
                        f"Bibliography key {key!r} is declared {len(locations)} times.",
                        path=first["path"],
                        line=first["line"],
                        details={"key": key},
                    )
                )
        for item in citation_uses:
            if item["key"] in bib_keys:
                continue
            issues.append(
                make_issue(
                    "UNDEFINED_CITATION",
                    f"Citation key {item['key']!r} has no matching bibliography entry.",
                    path=item["path"],
                    line=item["line"],
                    details={"key": item["key"]},
                )
            )

    metrics = {
        "files_scanned": scanned,
        "labels": len(labels),
        "references": len(references),
        "citation_uses": len(citation_uses),
        "bibliography_keys": len(bib_keys),
    }
    return emit_result(TOOL, issues, metrics, args)


if __name__ == "__main__":
    run_main(main)
