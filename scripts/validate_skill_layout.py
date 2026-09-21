"""Validate the local CUMCM skill layout and machine-facing metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_SKILLS = [
    "00-cumcm-orchestrator",
    "01-cumcm-doctor",
    "02-cumcm-brainstorm",
    "03-cumcm-project-start",
    "04-cumcm-modeling",
    "05-cumcm-coding-visual",
    "06-cumcm-result-mvp",
    "07-cumcm-drawio",
    "08-cumcm-template",
    "09-cumcm-writing",
    "10-cumcm-latex",
    "11-cumcm-verify",
    "12-cumcm-docx",
    "13-cumcm-paper-review",
]
CONTRACT_FIELDS = [
    "phase_id",
    "display_name",
    "owner_agent",
    "entry_conditions",
    "inputs",
    "outputs",
    "exit_conditions",
    "failure_return",
    "writable_paths",
    "read_only_paths",
    "invalidates",
    "user_gate",
]


def frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    result: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate local CUMCM skill metadata and directories.")
    parser.add_argument("--root", required=True, type=Path, help="Local project root.")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    skills_root = root / "skills"
    issues: list[dict[str, str]] = []
    checked = 0

    if not skills_root.is_dir():
        issues.append({"code": "SKILLS_ROOT_MISSING", "path": str(skills_root)})
    else:
        actual = {item.name for item in skills_root.iterdir() if item.is_dir()}
        for name in EXPECTED_SKILLS:
            skill_dir = skills_root / name
            if not skill_dir.is_dir():
                issues.append({"code": "SKILL_DIR_MISSING", "path": str(skill_dir)})
                continue
            checked += 1
            for required_dir in ("agents", "references", "scripts"):
                path = skill_dir / required_dir
                if not path.is_dir():
                    issues.append({"code": "REQUIRED_DIR_MISSING", "path": str(path)})
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                issues.append({"code": "SKILL_MD_MISSING", "path": str(skill_file)})
            else:
                try:
                    text = skill_file.read_text(encoding="utf-8")
                except (OSError, UnicodeError) as exc:
                    issues.append({"code": "SKILL_MD_UNREADABLE", "path": str(skill_file), "detail": str(exc)})
                    text = ""
                metadata = frontmatter(text)
                if metadata.get("name") != name:
                    issues.append({"code": "FRONTMATTER_NAME_MISMATCH", "path": str(skill_file)})
                if "description" not in metadata:
                    issues.append({"code": "FRONTMATTER_DESCRIPTION_MISSING", "path": str(skill_file)})
                missing = [field for field in CONTRACT_FIELDS if field not in text]
                if missing:
                    issues.append(
                        {
                            "code": "PHASE_CONTRACT_FIELD_MISSING",
                            "path": str(skill_file),
                            "detail": ",".join(missing),
                        }
                    )
            agent_file = skill_dir / "agents" / "openai.yaml"
            if not agent_file.is_file():
                issues.append({"code": "AGENT_CONFIG_MISSING", "path": str(agent_file)})
            else:
                try:
                    agent_text = agent_file.read_text(encoding="utf-8-sig")
                except (OSError, UnicodeError) as exc:
                    issues.append({"code": "AGENT_CONFIG_UNREADABLE", "path": str(agent_file), "detail": str(exc)})
                    agent_text = ""
                for key in ("display_name:", "short_description:", "default_prompt:"):
                    if key not in agent_text:
                        issues.append({"code": "AGENT_CONFIG_FIELD_MISSING", "path": str(agent_file), "detail": key})
        unexpected = sorted(actual - set(EXPECTED_SKILLS))
        for name in unexpected:
            issues.append({"code": "UNEXPECTED_SKILL_DIR", "path": str(skills_root / name)})

    payload = {"status": "PASS" if not issues else "ISSUES", "checked_skills": checked, "issues": issues}
    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"{payload['status']}: checked {checked} skill directories")
        for issue in issues:
            detail = f" ({issue['detail']})" if issue.get("detail") else ""
            print(f"- {issue['code']}: {issue['path']}{detail}")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())

