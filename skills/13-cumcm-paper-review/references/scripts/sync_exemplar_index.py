from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def find_project_root(script_path: Path) -> Path:
    for parent in script_path.resolve().parents:
        if (parent / ".agents").exists() and (parent / "math-modeling-intake").exists():
            return parent
    raise SystemExit("Could not find project root containing .agents and math-modeling-intake.")


def count_index_rows(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("| 20"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync generated exemplar index into the skill entrypoint.")
    parser.add_argument("--project-root", type=Path, default=None)
    args = parser.parse_args()

    project_root = args.project_root.resolve() if args.project_root else find_project_root(Path(__file__))
    source = project_root / "math-modeling-intake" / "_catalog" / "sample-index.md"
    target = (
        project_root
        / ".agents"
        / "skills"
        / "13-cumcm-paper-review"
        / "references"
        / "exemplars"
        / "index.md"
    )

    if not source.exists():
        raise SystemExit(f"Missing source index: {source}")

    text = source.read_text(encoding="utf-8")
    if "| 编号 | 年份 | 来源类型 | 标题 | 标签 | 关键词 | 卡片 |" not in text:
        raise SystemExit("Source index does not contain the expected card-path table header.")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(f"synced={target}")
    print(f"rows={count_index_rows(text)}")
    print(f"sha256={digest}")


if __name__ == "__main__":
    main()
