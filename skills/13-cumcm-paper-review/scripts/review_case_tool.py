from __future__ import annotations

import argparse
import datetime as _dt
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def require(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise SystemExit(f"Missing dependency: {module_name}. Use the bundled Codex Python runtime if possible.") from exc


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_stem(path: Path) -> str:
    return re.sub(r"[^0-9A-Za-z_.-]+", "_", path.stem).strip("_") or "paper"


def default_tool_paths() -> list[Path]:
    paths = [
        Path.home() / ".local" / "bin",
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        appdata_path = Path(appdata)
        paths.append(appdata_path / "npm")
        python_root = appdata_path / "Python"
        if python_root.exists():
            paths.extend(sorted(p / "Scripts" for p in python_root.glob("Python*") if (p / "Scripts").exists()))
    return paths


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def resolve_tool(name: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    found = shutil.which(name)
    if found:
        return found
    suffixes = [".cmd", ".exe", ""]
    for folder in default_tool_paths():
        for suffix in suffixes:
            candidate = folder / f"{name}{suffix}"
            if candidate.exists():
                return str(candidate)
    raise SystemExit(f"Cannot find {name}. Add it to PATH or pass --{name}.")


def tool_env() -> dict[str, str]:
    env = os.environ.copy()
    additions = [str(p) for p in default_tool_paths() if p.exists()]
    if additions:
        env["PATH"] = os.pathsep.join(additions + [env.get("PATH", "")])
    return env


def split_terms(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[,，;；、\n]+", raw)
    return [p.strip() for p in parts if p.strip()]


def unique_terms(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for group in groups:
        for term in group:
            normalized = term.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
    return result


def slug_text(value: str, fallback: str = "source") -> str:
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff-]+", "-", value).strip("-")
    return slug[:60] or fallback


KEY_ALIASES = {
    "页码": "page",
    "页面": "page",
    "定位": "target",
    "原文定位": "target",
    "类型": "type",
    "问题类型": "type",
    "提示": "message",
    "修改提示": "message",
    "搜索": "search",
    "搜索词": "search",
    "坐标": "bbox",
    "颜色": "color",
    "编号": "id",
    "图表类型": "visual_type",
    "本体内容": "visual_observation",
    "上下文位置": "context_position",
    "论文声称": "body_claim",
    "证据判断": "evidence_judgment",
    "数据可追溯性": "data_traceability",
    "需确认项": "needs_confirmation",
    "内容建议": "content_advice",
    "美化建议": "style_advice",
}


FIGURE_TYPE_RULES = [
    {
        "type": "流程图",
        "keywords": ["流程", "步骤", "思路", "框架", "决策树", "算法具体实现", "总体思路", "问题分析"],
        "function": "交代建模路线、算法执行顺序或问题拆解关系。",
        "review_focus": ["节点是否覆盖正文步骤", "箭头方向是否正确", "输入输出和终止条件是否清楚"],
        "style_advice": "用浅底色和少量层级，统一节点大小，避免把大段正文塞进节点。",
    },
    {
        "type": "模型结构图",
        "keywords": ["结构", "模型", "系统", "机理", "原理", "示意"],
        "function": "解释模型模块、物理/业务机理或变量关系。",
        "review_focus": ["变量关系是否与公式一致", "模块输入输出是否完整", "并列关系和因果关系是否混淆"],
        "style_advice": "突出关键变量和模块边界，减少装饰线条，补充必要图例。",
    },
    {
        "type": "数据分布图",
        "keywords": ["分布", "占比", "比例", "结构", "排名", "产量", "销售量", "面积", "频数"],
        "function": "说明样本构成、变量分布或数据预处理依据。",
        "review_focus": ["样本范围和分母口径", "分组阈值来源", "异常值和缺失值处理"],
        "style_advice": "优先用条形图或帕累托图表达类别比较，保留样本数、单位和分组规则。",
    },
    {
        "type": "趋势图",
        "keywords": ["折线", "趋势", "变化", "随时间", "时间", "年份", "曲线", "进化"],
        "function": "展示变量随时间、迭代或参数变化的趋势。",
        "review_focus": ["时间轴和单位", "平滑/归一化方法", "是否需要置信区间或基线"],
        "style_advice": "减少过密刻度，标清单位，必要时加入误差带、关键节点或对比线。",
    },
    {
        "type": "对比图",
        "keywords": ["对比", "比较", "不同", "关系图", "影响", "收益", "利润", "成本", "收入"],
        "function": "比较不同方案、类别、参数或模型结果。",
        "review_focus": ["比较口径是否一致", "评价指标是否公平", "是否只展示有利结果"],
        "style_advice": "统一坐标尺度和颜色含义，突出最优/基准方案，避免 3D 和过度装饰。",
    },
    {
        "type": "敏感性分析图",
        "keywords": ["敏感", "灵敏", "参数", "扰动", "波动", "p、q", "p,q", "影响"],
        "function": "说明参数变化对目标函数或决策结果的影响。",
        "review_focus": ["参数范围来源", "步长和控制变量", "结论是否覆盖边界情形"],
        "style_advice": "标出参数范围、基准点和稳定区间，必要时用热力图或多曲线对比。",
    },
    {
        "type": "空间/几何图",
        "keywords": ["坐标", "位置", "路径", "空间", "区域", "几何", "螺线", "螺旋", "路线", "把手", "耕地"],
        "function": "呈现空间位置、几何关系、路径规划或区域划分。",
        "review_focus": ["坐标系和单位", "几何约束是否与公式一致", "路径/区域是否回应题目约束"],
        "style_advice": "补坐标轴、比例尺、方向和关键点标注，避免颜色含义不明。",
    },
    {
        "type": "结果表",
        "keywords": ["结果", "决策", "方案", "指标", "总结", "目录", "利润期望", "变量序列"],
        "function": "汇总模型输出、方案选择、指标值或附录支撑材料。",
        "review_focus": ["列名和单位", "有效数字", "最优值标识", "能否追溯到模型输出或脚本"],
        "style_advice": "精简列数，标出关键值，长表移至附录，正文保留核心结果。",
    },
]


PROBLEM_TAGS = {
    "优化",
    "预测",
    "评价",
    "分类",
    "仿真",
    "机理建模",
    "统计分析",
    "图论网络",
    "时间序列",
    "空间分析",
    "多目标决策",
    "风险评估",
}

METHOD_TAGS = {
    "线性规划",
    "非线性规划",
    "整数规划",
    "动态规划",
    "层次分析法",
    "熵权法",
    "TOPSIS",
    "主成分分析",
    "回归分析",
    "聚类",
    "分类模型",
    "时间序列模型",
    "灰色预测",
    "微分方程",
    "蒙特卡洛",
    "灵敏度分析",
    "敏感性分析",
    "机器学习",
    "遗传算法",
}

DATA_TAGS = {
    "表格数据",
    "时间序列",
    "空间地理",
    "图像数据",
    "文本数据",
    "多源数据",
    "缺失数据",
    "小样本",
    "大规模数据",
    "公开数据",
    "自建指标",
}

WRITING_TAGS = {
    "摘要定量清晰",
    "问题分析强",
    "模型路线清晰",
    "公式解释充分",
    "结果解释充分",
    "检验完整",
    "图表组织好",
    "附录规范",
    "语言凝练",
    "结构层次清楚",
    "多问题结构",
    "算法表达",
    "代码依赖",
    "附录",
}

FIGURE_TAGS = {
    "图表密集",
    "流程图",
    "模型结构图",
    "数据分布图",
    "趋势图",
    "热力图",
    "空间图",
    "对比图",
    "敏感性分析图",
    "误差图",
    "排名表",
    "指标体系表",
}

RISK_TAGS = {
    "题型不匹配",
    "方法较复杂",
    "图表依赖强",
    "数据条件特殊",
    "摘要不可学",
    "格式不可学",
    "结论表达弱",
    "待人工复核",
    "scan-like",
    "image-folder",
}


def case_dirs(case_dir: Path) -> dict[str, Path]:
    return {
        "case": case_dir,
        "problem": case_dir / "problem",
        "paper": case_dir / "paper-original",
        "reviewed": case_dir / "reviewed",
        "work": case_dir / "work",
    }


def ensure_case_dirs(case_dir: Path) -> dict[str, Path]:
    dirs = case_dirs(case_dir)
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def first_file(folder: Path, suffixes: tuple[str, ...]) -> Path | None:
    if not folder.exists():
        return None
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in suffixes]
    return sorted(files, key=lambda p: p.name.lower())[0] if files else None


def copy_inputs(args: argparse.Namespace) -> None:
    case_dir = Path(args.case_dir).resolve()
    dirs = ensure_case_dirs(case_dir)
    copied: list[dict[str, str]] = []

    for src in [Path(p).resolve() for p in args.problem or []]:
        dst = dirs["problem"] / src.name
        shutil.copy2(src, dst)
        copied.append({"kind": "problem", "src": str(src), "dst": str(dst)})

    for src in [Path(p).resolve() for p in args.paper or []]:
        dst = dirs["paper"] / src.name
        shutil.copy2(src, dst)
        copied.append({"kind": "paper", "src": str(src), "dst": str(dst)})

    write_json(dirs["work"] / "case_inputs.json", {"case_dir": str(case_dir), "copied": copied})
    print(f"case_dir={case_dir}")
    print(f"copied={len(copied)}")


def default_template(format_name: str) -> str:
    if format_name == "docx":
        return """# DOCX Issues Draft

说明：每条意见用 --- 分隔。DOCX 必填 target/type/message。

---
target: 原文中用于定位的一段短句
type: 建议
message: |
  问题/建议/需确认：一句话指出问题。
  原因：说明为什么影响评审或表达。
  改法：给出可执行修改方式。
---
"""
    return """# PDF Issues Draft

说明：每条意见用 --- 分隔。PDF 必填 page/target/type/message，并且 search 或 bbox 至少填一个。
bbox 格式为 x0, top, x1, bottom；坐标来自 pdfplumber 页面坐标。

---
page: 1
target: 原文定位短语或图表名称
type: 建议
message: |
  问题/建议/需确认：一句话指出问题。
  原因：说明为什么影响评审或表达。
  改法：给出可执行修改方式。
search: 原文可搜索短语
bbox:
color: orange
---
"""


def make_issues_template(args: argparse.Namespace) -> None:
    case_dir = Path(args.case_dir).resolve() if args.case_dir else None
    out = Path(args.out).resolve() if args.out else None
    if out is None:
        if case_dir is None:
            raise SystemExit("Pass --case-dir or --out.")
        out = case_dir / "work" / f"{args.format}_issues_draft.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(default_template(args.format), encoding="utf-8")
    print(f"template={out}")


def normalize_key(key: str) -> str:
    key = key.strip()
    return KEY_ALIASES.get(key, key)


def parse_bbox(value: str) -> list[float] | None:
    value = value.strip()
    if not value:
        return None
    value = value.strip("[]")
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if len(parts) != 4:
        raise ValueError("bbox must contain four numbers: x0, top, x1, bottom")
    return [float(part) for part in parts]


def parse_issue_block(block: str) -> dict[str, Any]:
    item: dict[str, Any] = {}
    lines = block.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        match = re.match(r"^([^:：]+)[:：]\s*(.*)$", line)
        if not match:
            index += 1
            continue
        key = normalize_key(match.group(1))
        value = match.group(2).strip()
        if value == "|":
            index += 1
            collected: list[str] = []
            while index < len(lines):
                next_line = lines[index]
                if re.match(r"^[^:\s：][^:：]*[:：]", next_line):
                    index -= 1
                    break
                collected.append(next_line[2:] if next_line.startswith("  ") else next_line)
                index += 1
            item[key] = "\n".join(collected).strip()
        elif key == "page" and value:
            item[key] = int(value)
        elif key == "bbox":
            bbox = parse_bbox(value)
            if bbox is not None:
                item[key] = bbox
        elif value:
            item[key] = value.strip("\"'")
        index += 1
    return item


def parse_issues_draft(text: str) -> list[dict[str, Any]]:
    blocks = re.split(r"(?m)^---\s*$", text)
    issues = [parse_issue_block(block) for block in blocks]
    return [issue for issue in issues if any(key in issue for key in ("target", "message", "page", "bbox", "search"))]


def validate_issues(issues: list[dict[str, Any]], format_name: str) -> list[str]:
    errors: list[str] = []
    for index, issue in enumerate(issues, 1):
        for key in ("target", "type", "message"):
            if not issue.get(key):
                errors.append(f"{index:02d}: missing {key}")
        if format_name == "pdf":
            if not issue.get("page"):
                errors.append(f"{index:02d}: missing page")
            if not issue.get("search") and not issue.get("bbox"):
                errors.append(f"{index:02d}: PDF issue needs search or bbox")
        if "bbox" in issue and (not isinstance(issue["bbox"], list) or len(issue["bbox"]) != 4):
            errors.append(f"{index:02d}: invalid bbox")
    return errors


def build_issues(args: argparse.Namespace) -> None:
    draft = Path(args.draft).resolve()
    case_dir = Path(args.case_dir).resolve() if args.case_dir else None
    out = Path(args.out).resolve() if args.out else None
    if out is None:
        if case_dir is None:
            out = draft.with_suffix(".json")
        else:
            out = case_dir / "work" / "issues.json"
    issues = parse_issues_draft(draft.read_text(encoding="utf-8"))
    errors = validate_issues(issues, args.format)
    if errors:
        print("Issue draft validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(2)
    write_json(out, issues)
    print(f"issues={len(issues)}")
    print(f"out={out}")


def classify_figure_caption(caption: str, sample_tags: list[str] | None = None) -> str:
    text = caption.lower()
    tags = " ".join(sample_tags or [])
    best_type = "其他图表"
    best_score = 0
    for rule in FIGURE_TYPE_RULES:
        score = 0
        for keyword in rule["keywords"]:
            if keyword.lower() in text or (len(keyword) >= 2 and keyword in tags):
                score += 1
        if rule["type"] == "结果表" and caption.strip().startswith("表"):
            score += 2
        if score > best_score:
            best_score = score
            best_type = rule["type"]
    return best_type


def clean_caption(caption: str) -> str:
    caption = re.sub(r"\s+", " ", caption).strip()
    caption = caption.strip("：:，,。；;")
    return caption


def extract_captions_from_pdf(path: Path, max_pages: int | None = None) -> list[dict[str, Any]]:
    pdfplumber = require("pdfplumber")
    caption_re = re.compile(r"([图表])\s*([0-9０-９一二三四五六七八九十]+(?:[-－.．]\d+)?)\s*([^\n]{0,80})")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    with pdfplumber.open(str(path)) as pdf:
        pages = pdf.pages[:max_pages] if max_pages else pdf.pages
        for page_number, page in enumerate(pages, 1):
            text = page.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
            for match in caption_re.finditer(text):
                title_part = clean_caption(match.group(3))
                if len(title_part) < 2:
                    continue
                if title_part[0] in "是中）的，,;；-－~ ":
                    continue
                if any(term in title_part for term in ["所示", "可知", "如下", "根据", "通过", "发现", "请建立", "请标注", "中可", "如图", "这给"]):
                    continue
                caption = clean_caption(match.group(0))
                if len(caption) < 4 or caption in seen:
                    continue
                if re.fullmatch(r"[图表]\s*[0-9０-９一二三四五六七八九十.．\-－]+[）)]?", caption):
                    continue
                if len(caption) > 90:
                    caption = caption[:90]
                seen.add(caption)
                records.append(
                    {
                        "page": page_number,
                        "kind": match.group(1),
                        "number": match.group(2),
                        "caption": caption,
                    }
                )
    return records


def load_manifest_samples(manifest: Path) -> tuple[Path, list[dict[str, Any]]]:
    data = read_json(manifest)
    if not isinstance(data, dict) or "samples" not in data:
        raise SystemExit("manifest must be math-modeling-intake/_catalog/manifest.json")
    root = manifest.parents[1]
    return root, data["samples"]


def build_figure_patterns(args: argparse.Namespace) -> None:
    manifest = Path(args.manifest).resolve()
    root, samples = load_manifest_samples(manifest)
    out = Path(args.out).resolve() if args.out else Path("math-modeling-review-cases") / "_learned" / "figure-patterns.json"
    md_out = Path(args.md_out).resolve() if args.md_out else out.with_suffix(".md")
    max_samples = args.max_samples if args.max_samples and args.max_samples > 0 else None
    text_rich = [sample for sample in samples if sample.get("source_type") == "pdf" and sample.get("text_status") == "text-rich"]
    if max_samples:
        text_rich = text_rich[:max_samples]

    examples_by_type: dict[str, list[dict[str, Any]]] = {}
    extracted_count = 0
    for sample in text_rich:
        pdf_path = root / sample["source_path"]
        if not pdf_path.exists():
            continue
        try:
            captions = extract_captions_from_pdf(pdf_path, args.max_pages)
        except Exception as exc:
            captions = []
            print(f"skip={sample.get('sample_id')} error={exc}", file=sys.stderr)
        for caption in captions:
            figure_type = classify_figure_caption(caption["caption"], sample.get("tags") or [])
            record = {
                "sample_id": sample.get("sample_id"),
                "year": sample.get("year"),
                "paper_title": sample.get("title"),
                "page": caption["page"],
                "kind": caption["kind"],
                "caption": caption["caption"],
            }
            examples_by_type.setdefault(figure_type, []).append(record)
            extracted_count += 1

    patterns = []
    for rule in FIGURE_TYPE_RULES:
        examples = examples_by_type.get(rule["type"], [])[: args.examples_per_type]
        patterns.append(
            {
                "type": rule["type"],
                "keywords": rule["keywords"],
                "function": rule["function"],
                "review_focus": rule["review_focus"],
                "default_style_advice": rule["style_advice"],
                "examples": examples,
            }
        )
    other_examples = examples_by_type.get("其他图表", [])[: args.examples_per_type]
    if other_examples:
        patterns.append(
            {
                "type": "其他图表",
                "keywords": [],
                "function": "暂未被规则识别的图表，需要人工结合上下文判断。",
                "review_focus": ["图表本体是否清晰", "正文引用是否充分", "数据和结论是否可追溯"],
                "default_style_advice": "按图表本体选择合适的坐标、图例、单位和版面位置。",
                "examples": other_examples,
            }
        )

    result = {
        "source": str(manifest),
        "method": "从 text-rich 优秀论文 PDF 文本层抽取图/表标题，并按标题关键词归类；分类结果用于模板提示，不替代人工图审。",
        "sample_count": len(text_rich),
        "caption_count": extracted_count,
        "patterns": patterns,
    }
    write_json(out, result)

    lines = ["# 图表类型模式库", "", f"- 来源：{manifest}", f"- text-rich 样例数：{len(text_rich)}", f"- 抽取图表标题数：{extracted_count}", ""]
    for pattern in patterns:
        lines.append(f"## {pattern['type']}")
        lines.append("")
        lines.append(f"- 功能：{pattern['function']}")
        lines.append(f"- 检查重点：{'；'.join(pattern['review_focus'])}")
        lines.append(f"- 默认美化建议：{pattern['default_style_advice']}")
        if pattern["examples"]:
            lines.append("- 优秀论文标题示例：")
            for example in pattern["examples"][:5]:
                lines.append(f"  - {example['sample_id']} p{example['page']}: {example['caption']}")
        lines.append("")
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text("\n".join(lines), encoding="utf-8")
    print(f"samples={len(text_rich)}")
    print(f"captions={extracted_count}")
    print(f"patterns={out}")
    print(f"report={md_out}")


def figure_review_template(format_name: str) -> str:
    locator = "page: 1\nsearch: 图表标题或正文引用句\nbbox:" if format_name == "pdf" else "target: 图表标题、表题或正文引用句"
    return f"""# Figure Review Draft

说明：每条图审记录用 --- 分隔。先写证据链，再由 build-figure-issues 转成 issues.json。

---
id: fig-001
{locator}
title: 图表标题或表题
visual_type: 流程图/模型结构图/数据分布图/趋势图/对比图/敏感性分析图/空间/几何图/结果表/其他图表
context_position: 所在章节、图题/表题、正文引用句
body_claim: 正文用它支撑什么结论
visual_observation: 实际看到的主要元素、变量、坐标、节点或列名
evidence_judgment: 支持/部分支持/不支持/无法判断
data_traceability: 能否追溯到原始数据、计算口径、脚本或模型输出
needs_confirmation: 需要作者补充的原始数据、生成方法、脚本或中间结果
content_advice: 内容修正建议
style_advice: 字号、线宽、配色、图例、坐标轴、单位、版面等美化建议
color: blue
---
"""


def make_figure_review_template(args: argparse.Namespace) -> None:
    case_dir = Path(args.case_dir).resolve() if args.case_dir else None
    out = Path(args.out).resolve() if args.out else None
    if out is None:
        if case_dir is None:
            raise SystemExit("Pass --case-dir or --out.")
        out = case_dir / "work" / f"{args.format}_figure_review_draft.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(figure_review_template(args.format), encoding="utf-8")
    print(f"template={out}")


def validate_figure_records(records: list[dict[str, Any]], format_name: str) -> list[str]:
    errors: list[str] = []
    required = ["title", "visual_type", "visual_observation", "evidence_judgment", "content_advice", "style_advice"]
    allowed_judgments = {"支持", "部分支持", "不支持", "无法判断"}
    allowed_types = {rule["type"] for rule in FIGURE_TYPE_RULES} | {"其他图表"}
    for index, record in enumerate(records, 1):
        for key in required:
            if not record.get(key):
                errors.append(f"{index:02d}: missing {key}")
        if record.get("evidence_judgment") and record["evidence_judgment"] not in allowed_judgments:
            errors.append(f"{index:02d}: evidence_judgment must be one of {', '.join(sorted(allowed_judgments))}")
        if record.get("visual_type") and record["visual_type"] not in allowed_types:
            errors.append(f"{index:02d}: unknown visual_type {record['visual_type']}")
        if format_name == "pdf":
            if not record.get("page"):
                errors.append(f"{index:02d}: missing page")
            if not record.get("search") and not record.get("bbox"):
                errors.append(f"{index:02d}: PDF figure record needs search or bbox")
        else:
            if not record.get("target") and not record.get("title"):
                errors.append(f"{index:02d}: DOCX figure record needs target or title")
    return errors


def figure_record_to_issue(record: dict[str, Any], format_name: str) -> dict[str, Any]:
    judgment = record.get("evidence_judgment", "无法判断")
    issue_type = "图表建议"
    if "无法" in judgment or record.get("needs_confirmation"):
        issue_type = "需确认"
    elif "不支持" in judgment:
        issue_type = "问题"
    message_parts = [
        f"{issue_type}：{record.get('title', record.get('target', '该图表'))} 的证据判断为“{judgment}”。",
    ]
    if record.get("visual_observation"):
        message_parts.append(f"本体观察：{record['visual_observation']}")
    if record.get("body_claim"):
        message_parts.append(f"正文声称：{record['body_claim']}")
    if record.get("data_traceability"):
        message_parts.append(f"数据追溯：{record['data_traceability']}")
    if record.get("needs_confirmation"):
        message_parts.append(f"请提供：{record['needs_confirmation']}")
    if record.get("content_advice"):
        message_parts.append(f"内容改法：{record['content_advice']}")
    if record.get("style_advice"):
        message_parts.append(f"美化建议：{record['style_advice']}")

    target = record.get("target") or record.get("title") or record.get("search") or "图表位置"
    issue: dict[str, Any] = {
        "target": target,
        "type": issue_type,
        "message": "\n".join(message_parts),
        "color": record.get("color", "blue"),
    }
    if format_name == "pdf":
        issue["page"] = int(record["page"])
        if record.get("search"):
            issue["search"] = record["search"]
        if record.get("bbox"):
            issue["bbox"] = record["bbox"]
    return issue


def build_figure_issues(args: argparse.Namespace) -> None:
    draft = Path(args.draft).resolve()
    case_dir = Path(args.case_dir).resolve() if args.case_dir else None
    out = Path(args.out).resolve() if args.out else None
    records_out = Path(args.records_out).resolve() if args.records_out else None
    if out is None:
        out = (case_dir / "work" / "figure_issues.json") if case_dir else draft.with_name("figure_issues.json")
    if records_out is None:
        records_out = (case_dir / "work" / "figure_review.json") if case_dir else draft.with_name("figure_review.json")
    records = parse_issues_draft(draft.read_text(encoding="utf-8"))
    errors = validate_figure_records(records, args.format)
    if errors:
        print("Figure review validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(2)
    issues = [figure_record_to_issue(record, args.format) for record in records]
    write_json(records_out, records)
    write_json(out, issues)
    print(f"figure_records={len(records)}")
    print(f"records={records_out}")
    print(f"issues={out}")


def extract_docx_text(path: Path) -> str:
    docx = require("docx")
    doc = docx.Document(str(path))
    parts: list[str] = []

    def add_paragraphs(paragraphs) -> None:
        for paragraph in paragraphs:
            text = paragraph.text.strip()
            if text:
                parts.append(text)

    add_paragraphs(doc.paragraphs)
    for table_index, table in enumerate(doc.tables, 1):
        parts.append(f"\n[table {table_index}]")
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " / ") for cell in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def rough_extract_doc_text(path: Path) -> str:
    data = path.read_bytes()
    chunks: list[str] = []
    pattern = r"[\u4e00-\u9fffA-Za-z0-9，。、“”：（）()；;：:《》\-—_\s]{8,}"
    for encoding in ("utf-16le", "gb18030", "latin1"):
        text = data.decode(encoding, errors="ignore")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", text)
        chunks.append("\n".join(re.findall(pattern, text)))
    merged = "\n".join(chunks)
    merged = re.sub(r"[ \t]{2,}", " ", merged)
    merged = re.sub(r"\n{3,}", "\n\n", merged)
    return merged.strip()


def extract_pdf_text(path: Path) -> tuple[str, str]:
    pdfplumber = require("pdfplumber")
    full_parts: list[str] = []
    profile: list[str] = [f"# {path.stem} PDF text profile", ""]
    with pdfplumber.open(str(path)) as pdf:
        profile.append(f"- pages: {len(pdf.pages)}")
        for page_number, page in enumerate(pdf.pages, 1):
            text = page.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
            words = page.extract_words(x_tolerance=1.5, y_tolerance=3) or []
            images = page.images or []
            profile.append(
                f"- page {page_number}: chars={len(text)} words={len(words)} "
                f"images={len(images)} size={page.width:.1f}x{page.height:.1f}"
            )
            full_parts.append(f"\n\n===== PAGE {page_number} =====\n{text}")
    return "\n".join(full_parts), "\n".join(profile)


def extract_case(args: argparse.Namespace) -> None:
    case_dir = Path(args.case_dir).resolve()
    dirs = ensure_case_dirs(case_dir)
    work = dirs["work"]
    reports: list[dict[str, str]] = []

    for folder_key in ("problem", "paper"):
        folder = dirs[folder_key]
        for path in sorted(p for p in folder.iterdir() if p.is_file()):
            suffix = path.suffix.lower()
            out_base = work / safe_stem(path)
            if suffix == ".docx":
                text = extract_docx_text(path)
                out = out_base.with_name(f"{out_base.name}_text.txt")
                out.write_text(text, encoding="utf-8")
                reports.append({"file": str(path), "kind": "docx", "text": str(out), "chars": str(len(text))})
            elif suffix == ".doc":
                text = rough_extract_doc_text(path)
                out = out_base.with_name(f"{out_base.name}_rough_text.txt")
                out.write_text(text, encoding="utf-8")
                reports.append({"file": str(path), "kind": "doc-rough", "text": str(out), "chars": str(len(text))})
            elif suffix == ".pdf":
                text, profile = extract_pdf_text(path)
                text_out = out_base.with_name(f"{out_base.name}_full_text.txt")
                profile_out = out_base.with_name(f"{out_base.name}_pdf_profile.md")
                text_out.write_text(text, encoding="utf-8")
                profile_out.write_text(profile, encoding="utf-8")
                reports.append(
                    {"file": str(path), "kind": "pdf", "text": str(text_out), "profile": str(profile_out), "chars": str(len(text))}
                )

    write_json(work / "extraction_report.json", reports)
    print(f"extracted={len(reports)}")


def render_pdf_pages(pdf_path: Path, out_dir: Path, scale: float) -> list[Path]:
    pdfium = require("pypdfium2")
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(pdf_path))
    paths: list[Path] = []
    for index, page in enumerate(doc, 1):
        image = page.render(scale=scale).to_pil().convert("RGB")
        out = out_dir / f"{safe_stem(pdf_path)}_page-{index:02d}.png"
        image.save(out, quality=92)
        paths.append(out)
    return paths


def make_contact_sheet(image_paths: list[Path], out: Path, cols: int, thumb_w: int) -> None:
    Image = require("PIL.Image")
    ImageDraw = require("PIL.ImageDraw")
    thumbs = []
    for image_path in image_paths:
        with Image.open(image_path).convert("RGB") as img:
            ratio = thumb_w / img.width
            thumb_h = int(img.height * ratio)
            img = img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            tile = Image.new("RGB", (thumb_w, thumb_h + 30), "white")
            tile.paste(img, (0, 30))
            ImageDraw.Draw(tile).text((8, 8), image_path.stem, fill=(0, 0, 0))
            thumbs.append(tile)
    if not thumbs:
        return
    rows = (len(thumbs) + cols - 1) // cols
    cell_h = max(tile.height for tile in thumbs)
    sheet = Image.new("RGB", (cols * thumb_w, rows * cell_h), "white")
    for index, tile in enumerate(thumbs):
        sheet.paste(tile, ((index % cols) * thumb_w, (index // cols) * cell_h))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=92)


def collect_pdf_inventory(pdf_path: Path) -> str:
    records = collect_pdf_figure_inventory(pdf_path)
    return figure_inventory_to_markdown(pdf_path.stem, records)


def caption_kind(caption: str) -> str:
    return "表" if caption.strip().startswith("表") else "图"


def caption_records_from_text(text: str, page_number: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    caption_re = re.compile(r"^\s*((?:图|表)\s*\d+(?:[.\-－、]\d+)?[^\n]{0,90})")
    for line_number, line in enumerate(text.splitlines(), 1):
        match = caption_re.search(line.strip())
        if not match:
            continue
        title = match.group(1).strip()
        record: dict[str, Any] = {
            "id": f"cap-{len(records) + 1:03d}",
            "source_type": "caption",
            "kind": caption_kind(title),
            "title": title,
            "visual_type": classify_figure_caption(title),
            "line": line_number,
            "review_status": "待图审",
            "needs_confirmation": "",
        }
        if page_number is not None:
            record["page"] = page_number
        records.append(record)
    return records


def collect_pdf_figure_inventory(pdf_path: Path) -> list[dict[str, Any]]:
    pdfplumber = require("pdfplumber")
    records: list[dict[str, Any]] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            text = page.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
            for caption in caption_records_from_text(text, page_number):
                caption["id"] = f"pdf-p{page_number:03d}-{caption['id']}"
                records.append(caption)
            for index, image in enumerate(page.images or [], 1):
                bbox = [
                    float(image.get("x0", 0)),
                    float(image.get("top", 0)),
                    float(image.get("x1", 0)),
                    float(image.get("bottom", 0)),
                ]
                records.append(
                    {
                        "id": f"pdf-p{page_number:03d}-img-{index:02d}",
                        "source_type": "embedded-image",
                        "kind": "图",
                        "title": "",
                        "visual_type": "待判定",
                        "page": page_number,
                        "bbox": bbox,
                        "width": float(image.get("width", 0)),
                        "height": float(image.get("height", 0)),
                        "review_status": "待图审",
                        "needs_confirmation": "",
                    }
                )
    return records


def collect_docx_figure_inventory(docx_path: Path) -> list[dict[str, Any]]:
    docx = require("docx")
    Image = require("PIL.Image")
    records: list[dict[str, Any]] = []
    doc = docx.Document(str(docx_path))
    paragraphs = [paragraph.text.strip() for paragraph in iter_docx_paragraphs(doc) if paragraph.text.strip()]
    for index, text in enumerate(paragraphs, 1):
        for caption in caption_records_from_text(text):
            caption["id"] = f"docx-p{index:04d}-{caption['id']}"
            caption["paragraph_index"] = index
            caption["context_before"] = paragraphs[index - 2] if index >= 2 else ""
            caption["context_after"] = paragraphs[index] if index < len(paragraphs) else ""
            records.append(caption)

    with zipfile.ZipFile(docx_path) as archive:
        media_names = [name for name in archive.namelist() if name.startswith("word/media/")]
        for index, name in enumerate(media_names, 1):
            width = height = size = 0
            try:
                data = archive.read(name)
                size = len(data)
                from io import BytesIO

                with Image.open(BytesIO(data)) as img:
                    width, height = img.width, img.height
            except Exception:
                pass
            records.append(
                {
                    "id": f"docx-media-{index:03d}",
                    "source_type": "embedded-media",
                    "kind": "图",
                    "title": "",
                    "visual_type": "待判定",
                    "media_name": Path(name).name,
                    "width": width,
                    "height": height,
                    "bytes": size,
                    "review_status": "待图审",
                    "needs_confirmation": "",
                }
            )
    return records


def figure_inventory_to_markdown(title: str, records: list[dict[str, Any]]) -> str:
    lines = [f"# {title} figure/table inventory", ""]
    if not records:
        lines.append("未自动发现图表标题或内嵌图片；正式审稿仍需人工检查页面渲染。")
        return "\n".join(lines) + "\n"
    lines.extend(
        [
            "| id | page/position | kind | source | title/media | visual_type | bbox/size | status |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for record in records:
        position = str(record.get("page") or record.get("paragraph_index") or "")
        title_or_media = record.get("title") or record.get("media_name") or ""
        bbox = record.get("bbox")
        if bbox:
            bbox_or_size = ", ".join(f"{float(value):.1f}" for value in bbox)
        elif record.get("width") or record.get("height"):
            bbox_or_size = f"{record.get('width', 0)}x{record.get('height', 0)}"
        else:
            bbox_or_size = ""
        lines.append(
            "| {id} | {position} | {kind} | {source} | {title} | {visual_type} | {bbox} | {status} |".format(
                id=record.get("id", ""),
                position=position,
                kind=record.get("kind", ""),
                source=record.get("source_type", ""),
                title=str(title_or_media).replace("|", "/"),
                visual_type=record.get("visual_type", ""),
                bbox=bbox_or_size,
                status=record.get("review_status", ""),
            )
        )
    lines.append("")
    lines.append("说明：该清单只负责防漏审；每条图表是否合理仍需回到图表本体、正文引用、上下文和数据来源。")
    return "\n".join(lines) + "\n"


def build_figure_inventory(args: argparse.Namespace) -> None:
    case_dir = Path(args.case_dir).resolve()
    dirs = ensure_case_dirs(case_dir)
    source_format = args.format
    file_path: Path | None = Path(args.file).resolve() if args.file else None
    if source_format == "auto":
        if file_path:
            suffix = file_path.suffix.lower()
            source_format = "docx" if suffix == ".docx" else "pdf" if suffix == ".pdf" else "auto"
        else:
            file_path = first_file(dirs["paper"], (".pdf", ".docx"))
            if file_path:
                source_format = "docx" if file_path.suffix.lower() == ".docx" else "pdf"
    if not file_path:
        suffixes = (".docx",) if source_format == "docx" else (".pdf",)
        file_path = first_file(dirs["paper"], suffixes)
    if not file_path or source_format not in {"pdf", "docx"}:
        raise SystemExit("No supported paper found. Pass --file with a .pdf or .docx, or place one in paper-original/.")

    if source_format == "pdf":
        records = collect_pdf_figure_inventory(file_path)
    else:
        records = collect_docx_figure_inventory(file_path)

    out_json = Path(args.out).resolve() if args.out else dirs["work"] / "figure_inventory.json"
    out_md = Path(args.md_out).resolve() if args.md_out else dirs["work"] / "figure_inventory.md"
    data = {
        "source_file": str(file_path),
        "format": source_format,
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "records": records,
        "review_rule": "清单用于防漏审；正式图审必须补充图表本体、正文引用、上下文、证据判断和需确认项。",
    }
    write_json(out_json, data)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(figure_inventory_to_markdown(file_path.stem, records), encoding="utf-8")
    print(f"inventory_records={len(records)}")
    print(f"inventory_json={out_json}")
    print(f"inventory_md={out_md}")


def render_case_pdf(args: argparse.Namespace) -> None:
    case_dir = Path(args.case_dir).resolve()
    dirs = ensure_case_dirs(case_dir)
    pdf_path = Path(args.pdf).resolve() if args.pdf else first_file(dirs["paper"], (".pdf",))
    if not pdf_path:
        raise SystemExit("No PDF found. Pass --pdf or place a PDF in paper-original/.")
    rendered = render_pdf_pages(pdf_path, dirs["work"] / "rendered_pages", args.scale)
    contact = dirs["work"] / f"{safe_stem(pdf_path)}_all_pages_contact_sheet.jpg"
    make_contact_sheet(rendered, contact, args.cols, args.thumb_width)
    inventory_records = collect_pdf_figure_inventory(pdf_path)
    inventory = figure_inventory_to_markdown(pdf_path.stem, inventory_records)
    inventory_path = dirs["work"] / f"{safe_stem(pdf_path)}_figure_table_inventory.md"
    inventory_json = dirs["work"] / "figure_inventory.json"
    write_json(
        inventory_json,
        {
            "source_file": str(pdf_path),
            "format": "pdf",
            "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "records": inventory_records,
            "review_rule": "清单用于防漏审；正式图审必须补充图表本体、正文引用、上下文、证据判断和需确认项。",
        },
    )
    inventory_path.write_text(inventory, encoding="utf-8")
    print(f"pages={len(rendered)}")
    print(f"contact_sheet={contact}")
    print(f"inventory={inventory_path}")
    print(f"inventory_json={inventory_json}")


def inspect_docx_media(args: argparse.Namespace) -> None:
    Image = require("PIL.Image")
    ImageDraw = require("PIL.ImageDraw")
    case_dir = Path(args.case_dir).resolve()
    dirs = ensure_case_dirs(case_dir)
    docx_path = Path(args.docx).resolve() if args.docx else first_file(dirs["paper"], (".docx",))
    if not docx_path:
        raise SystemExit("No DOCX found. Pass --docx or place a DOCX in paper-original/.")

    out_dir = dirs["work"] / "media"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, int, int, int]] = []
    with zipfile.ZipFile(docx_path) as archive:
        names = [name for name in archive.namelist() if name.startswith("word/media/")]
        for name in names:
            out = out_dir / Path(name).name
            out.write_bytes(archive.read(name))
            try:
                with Image.open(out) as img:
                    rows.append((out.name, img.width, img.height, out.stat().st_size))
            except Exception:
                rows.append((out.name, 0, 0, out.stat().st_size))

    rows.sort(key=lambda item: (item[1] * item[2], item[3]), reverse=True)
    report = ["| file | width | height | bytes |", "|---|---:|---:|---:|"]
    for name, width, height, size in rows:
        report.append(f"| {name} | {width} | {height} | {size} |")
    (dirs["work"] / "media_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    thumbs = []
    for name, width, height, _ in rows[: args.limit]:
        if width <= 0 or height <= 0:
            continue
        with Image.open(out_dir / name).convert("RGB") as img:
            img.thumbnail((260, 180))
            tile = Image.new("RGB", (280, 220), "white")
            tile.paste(img, ((280 - img.width) // 2, 10))
            ImageDraw.Draw(tile).text((10, 195), f"{name} {width}x{height}", fill=(0, 0, 0))
            thumbs.append(tile)
    if thumbs:
        cols = 3
        sheet = Image.new("RGB", (cols * 280, ((len(thumbs) + cols - 1) // cols) * 220), "white")
        for index, tile in enumerate(thumbs):
            sheet.paste(tile, ((index % cols) * 280, (index // cols) * 220))
        sheet.save(dirs["work"] / "media_contact_sheet.jpg", quality=90)
    inventory_records = collect_docx_figure_inventory(docx_path)
    write_json(
        dirs["work"] / "figure_inventory.json",
        {
            "source_file": str(docx_path),
            "format": "docx",
            "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "records": inventory_records,
            "review_rule": "DOCX 无稳定页码；清单用段落位置、图题/表题和内嵌媒体防漏审。",
        },
    )
    (dirs["work"] / "figure_inventory.md").write_text(figure_inventory_to_markdown(docx_path.stem, inventory_records), encoding="utf-8")
    print(f"media={len(rows)}")
    print(f"inventory_records={len(inventory_records)}")


def iter_docx_paragraphs(doc):
    for paragraph in doc.paragraphs:
        yield paragraph
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    yield paragraph


def insert_paragraph_after(paragraph, text: str):
    oxml = require("docx.oxml")
    paragraph_module = require("docx.text.paragraph")
    OxmlElement = oxml.OxmlElement
    Paragraph = paragraph_module.Paragraph
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    run = new_para.add_run(text)
    return new_para, run


def highlight_paragraph(paragraph) -> None:
    enum_text = require("docx.enum.text")
    WD_COLOR_INDEX = enum_text.WD_COLOR_INDEX
    if not paragraph.runs and paragraph.text:
        paragraph.add_run("")
    for run in paragraph.runs:
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def style_docx_note(paragraph, run) -> None:
    shared = require("docx.shared")
    oxml = require("docx.oxml")
    ns = require("docx.oxml.ns")
    Pt = shared.Pt
    RGBColor = shared.RGBColor
    OxmlElement = oxml.OxmlElement
    qn = ns.qn
    paragraph.paragraph_format.left_indent = Pt(18)
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(8)
    run.font.name = "Microsoft YaHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    run.font.size = Pt(9)
    run.font.bold = True
    run.font.color.rgb = RGBColor(31, 78, 121)
    ppr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), "DDEBF7")
    ppr.append(shd)
    border = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "8")
    left.set(qn("w:space"), "4")
    left.set(qn("w:color"), "5B9BD5")
    border.append(left)
    ppr.append(border)


def write_docx_review(args: argparse.Namespace) -> None:
    docx = require("docx")
    case_dir = Path(args.case_dir).resolve()
    dirs = ensure_case_dirs(case_dir)
    src = Path(args.src).resolve() if args.src else first_file(dirs["paper"], (".docx",))
    if not src:
        raise SystemExit("No DOCX found. Pass --src or place a DOCX in paper-original/.")
    issues = read_json(Path(args.issues).resolve())
    out = Path(args.out).resolve() if args.out else dirs["reviewed"] / f"{safe_stem(src)}_reviewed.docx"
    artifact_stem = safe_stem(out) if args.out else safe_stem(src)
    notes_md = dirs["reviewed"] / f"{artifact_stem}_review_notes.md"
    notes_txt = dirs["reviewed"] / f"{artifact_stem}_review_notes.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out)

    doc = docx.Document(str(out))
    applied: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for index, issue in enumerate(issues, 1):
        target = str(issue.get("target", ""))
        paragraph = next((p for p in iter_docx_paragraphs(doc) if target and target in p.text), None)
        if paragraph is None:
            missing.append({"id": index, **issue})
            continue
        highlight_paragraph(paragraph)
        issue_type = issue.get("type") or issue.get("issue_type") or "建议"
        message = issue.get("message", "")
        note_text = f"【审阅提示 {index:02d}｜{issue_type}】{message}"
        note_para, note_run = insert_paragraph_after(paragraph, note_text)
        style_docx_note(note_para, note_run)
        applied.append({"id": index, **issue})
    doc.save(str(out))

    write_notes(notes_md, notes_txt, safe_stem(src), issues, applied, missing, args.labels, args.references, "DOCX")
    write_json(dirs["work"] / f"{artifact_stem}_docx_review_applied.json", {"applied": applied, "missing": missing})
    print(f"applied={len(applied)} missing={len(missing)} out={out}")


@dataclass
class Issue:
    page: int
    target: str
    issue_type: str
    message: str
    search: str | None
    bbox: tuple[float, float, float, float] | None
    color: str


def parse_pdf_issues(raw_issues: list[dict[str, Any]]) -> list[Issue]:
    issues: list[Issue] = []
    for raw in raw_issues:
        bbox = raw.get("bbox")
        parsed_bbox = tuple(float(x) for x in bbox) if bbox else None
        issues.append(
            Issue(
                page=int(raw["page"]),
                target=str(raw.get("target", "")),
                issue_type=str(raw.get("type") or raw.get("issue_type") or "建议"),
                message=str(raw.get("message", "")),
                search=raw.get("search"),
                bbox=parsed_bbox,  # type: ignore[arg-type]
                color=str(raw.get("color", "orange")),
            )
        )
    return issues


def find_pdf_bbox(pdf, issue: Issue):
    if issue.bbox:
        return issue.bbox
    if not issue.search:
        return None
    page = pdf.pages[issue.page - 1]
    hits = page.search(issue.search)
    if not hits:
        return None
    hit = hits[0]
    x0, top, x1, bottom = hit["x0"], hit["top"], hit["x1"], hit["bottom"]
    return max(30, x0 - 3), max(30, top - 3), min(page.width - 30, x1 + 3), min(page.height - 30, bottom + 3)


def draw_pdf_overlay(src: Path, overlay: Path, issues: list[Issue]) -> list[dict[str, Any]]:
    pdfplumber = require("pdfplumber")
    colors = require("reportlab.lib.colors")
    canvas = require("reportlab.pdfgen.canvas")
    color_map = {
        "orange": colors.Color(1.0, 0.55, 0.0),
        "blue": colors.Color(0.1, 0.38, 0.85),
        "green": colors.Color(0.0, 0.55, 0.25),
        "yellow": colors.Color(0.95, 0.65, 0.0),
    }
    applied: list[dict[str, Any]] = []
    with pdfplumber.open(str(src)) as pdf:
        c = canvas.Canvas(str(overlay), pagesize=(pdf.pages[0].width, pdf.pages[0].height))
        for page_number, page in enumerate(pdf.pages, 1):
            c.setPageSize((page.width, page.height))
            for index, issue in enumerate(issues, 1):
                if issue.page != page_number:
                    continue
                bbox = find_pdf_bbox(pdf, issue)
                if bbox is None:
                    applied.append({"id": index, "page": page_number, "status": "missing", "target": issue.target})
                    continue
                x0, top, x1, bottom = bbox
                y0 = page.height - bottom
                width = x1 - x0
                height = bottom - top
                color = color_map.get(issue.color, color_map["orange"])
                c.saveState()
                try:
                    c.setStrokeAlpha(0.95)
                except Exception:
                    pass
                c.setStrokeColor(color)
                c.setFillColor(color)
                c.setLineWidth(1.2)
                c.roundRect(x0, y0, width, height, 3, stroke=1, fill=0)
                label_x = min(page.width - 34, x1 + 4)
                label_y = min(page.height - 22, y0 + height + 2)
                if label_y < 18:
                    label_y = y0 + height + 4
                try:
                    c.setFillAlpha(1)
                except Exception:
                    pass
                c.circle(label_x + 8, label_y + 8, 8, stroke=0, fill=1)
                c.setFillColor(colors.white)
                c.setFont("Helvetica-Bold", 7)
                c.drawCentredString(label_x + 8, label_y + 5.5, str(index))
                c.restoreState()
                applied.append({"id": index, "page": page_number, "status": "applied", "target": issue.target, "bbox": bbox})
            c.showPage()
        c.save()
    return applied


def wrap_cjk(text: str, width: int) -> list[str]:
    lines: list[str] = []
    for para in text.splitlines() or [""]:
        if not para:
            lines.append("")
            continue
        current = ""
        for char in para:
            current += char
            if len(current) >= width:
                lines.append(current)
                current = ""
        if current:
            lines.append(current)
    return lines


def make_prompt_pages(out: Path, title: str, issues: list[Issue]) -> None:
    canvas = require("reportlab.pdfgen.canvas")
    colors = require("reportlab.lib.colors")
    pdfmetrics = require("reportlab.pdfbase.pdfmetrics")
    cidfonts = require("reportlab.pdfbase.cidfonts")
    UnicodeCIDFont = cidfonts.UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    width, height = 595.2756, 841.8898
    c = canvas.Canvas(str(out), pagesize=(width, height))
    c.setFont("STSong-Light", 15)
    c.drawString(48, height - 48, title)
    c.setFont("STSong-Light", 9)
    c.drawString(48, height - 66, "说明：原文页中的描边框和编号对应以下审阅提示。")
    y = height - 92
    for index, issue in enumerate(issues, 1):
        block = f"{index:02d}. 第 {issue.page} 页｜{issue.issue_type}｜定位：{issue.target}\n{issue.message}"
        lines = wrap_cjk(block, 55)
        needed = 14 * len(lines) + 14
        if y - needed < 50:
            c.showPage()
            c.setFont("STSong-Light", 10)
            y = height - 48
        c.setFillColor(colors.black)
        c.setFont("STSong-Light", 10)
        for line in lines:
            c.drawString(48, y, line)
            y -= 14
        y -= 8
    c.save()


def merge_reviewed_pdf(src: Path, overlay: Path, prompt_pages: Path, out: Path) -> None:
    pypdf = require("pypdf")
    src_pdf = pypdf.PdfReader(str(src))
    overlay_pdf = pypdf.PdfReader(str(overlay))
    notes_pdf = pypdf.PdfReader(str(prompt_pages))
    writer = pypdf.PdfWriter()
    for page, overlay_page in zip(src_pdf.pages, overlay_pdf.pages):
        page.merge_page(overlay_page)
        writer.add_page(page)
    for page in notes_pdf.pages:
        writer.add_page(page)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as handle:
        writer.write(handle)


def write_notes(
    notes_md: Path,
    notes_txt: Path,
    title: str,
    raw_issues: list[dict[str, Any]],
    applied: list[dict[str, Any]],
    missing: list[dict[str, Any]],
    labels: str | None,
    references: str | None,
    format_name: str,
) -> None:
    lines = [f"# {title} review notes", ""]
    if labels:
        lines.append(f"- 待审论文标签：{labels}")
    if references:
        lines.append(f"- 参考样例与外部检索：{references}")
    lines.append(f"- 标注方式：{format_name} 可见定位标记 + 通用文本提示清单。")
    lines.append("")
    for index, issue in enumerate(raw_issues, 1):
        issue_type = issue.get("type") or issue.get("issue_type") or "建议"
        lines.append(f"## {index:02d}. {issue_type}")
        lines.append("")
        if "page" in issue:
            lines.append(f"- 页码：{issue['page']}")
        lines.append(f"- 原文定位：{issue.get('target', '')}")
        lines.append(f"- 提示：{issue.get('message', '')}")
        lines.append("")
    if missing:
        lines.append("## 未定位项")
        for item in missing:
            lines.append(f"- {item.get('id')}: {item.get('target')}")
    text = "\n".join(lines)
    notes_md.parent.mkdir(parents=True, exist_ok=True)
    notes_md.write_text(text, encoding="utf-8")
    notes_txt.write_text(text, encoding="utf-8")


def write_pdf_review(args: argparse.Namespace) -> None:
    case_dir = Path(args.case_dir).resolve()
    dirs = ensure_case_dirs(case_dir)
    src = Path(args.src).resolve() if args.src else first_file(dirs["paper"], (".pdf",))
    if not src:
        raise SystemExit("No PDF found. Pass --src or place a PDF in paper-original/.")
    raw_issues = read_json(Path(args.issues).resolve())
    issues = parse_pdf_issues(raw_issues)
    stem = safe_stem(src)
    out = Path(args.out).resolve() if args.out else dirs["reviewed"] / f"{stem}_reviewed.pdf"
    artifact_stem = safe_stem(out) if args.out else stem
    overlay = dirs["work"] / f"{stem}_overlay.pdf"
    prompt_pages = dirs["work"] / f"{stem}_review_prompt_pages.pdf"
    notes_md = dirs["reviewed"] / f"{artifact_stem}_review_notes.md"
    notes_txt = dirs["reviewed"] / f"{artifact_stem}_review_notes.txt"

    applied = draw_pdf_overlay(src, overlay, issues)
    make_prompt_pages(prompt_pages, f"{stem} 审阅提示清单", issues)
    merge_reviewed_pdf(src, overlay, prompt_pages, out)
    missing = [item for item in applied if item.get("status") == "missing"]
    write_notes(notes_md, notes_txt, stem, raw_issues, applied, missing, args.labels, args.references, "PDF")
    write_json(dirs["work"] / f"{artifact_stem}_review_applied.json", {"applied": applied, "missing": missing})
    print(f"applied={len(applied) - len(missing)} missing={len(missing)} out={out}")


def rendered_page_stats(image_path: Path) -> dict[str, Any]:
    Image = require("PIL.Image")
    with Image.open(image_path).convert("RGB") as image:
        image.thumbnail((900, 1300))
        total = max(1, image.width * image.height)
        non_white = 0
        marker_pixels = 0
        pixels = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
        for r, g, b in pixels:
            if min(r, g, b) < 245:
                non_white += 1
            blue_marker = b > 135 and r < 130 and g < 170
            orange_marker = r > 170 and 65 < g < 190 and b < 110
            green_marker = g > 100 and r < 110 and b < 140
            yellow_marker = r > 185 and g > 130 and b < 120
            if blue_marker or orange_marker or green_marker or yellow_marker:
                marker_pixels += 1
        return {
            "image": str(image_path),
            "width": image.width,
            "height": image.height,
            "non_white_ratio": round(non_white / total, 6),
            "marker_pixels": marker_pixels,
        }


def build_pdf_render_acceptance(
    rendered_by_page: dict[int, Path],
    applied: list[dict[str, Any]],
    original_pages: int,
    reviewed_pages: int,
    min_marker_pixels: int,
    min_non_white_ratio: float,
) -> dict[str, Any]:
    applied_pages = sorted({int(item["page"]) for item in applied if item.get("status") == "applied"})
    prompt_pages = list(range(original_pages + 1, reviewed_pages + 1))
    page_checks: list[dict[str, Any]] = []
    for page_number, image_path in sorted(rendered_by_page.items()):
        stats = rendered_page_stats(image_path)
        check = {
            "page": page_number,
            **stats,
            "is_prompt_page": page_number in prompt_pages,
            "has_applied_marker": page_number in applied_pages,
            "non_blank_ok": stats["non_white_ratio"] >= min_non_white_ratio,
            "marker_pixels_ok": True,
        }
        if page_number in applied_pages:
            check["marker_pixels_ok"] = stats["marker_pixels"] >= min_marker_pixels
        page_checks.append(check)

    marker_checks = [item for item in page_checks if item["has_applied_marker"]]
    prompt_checks = [item for item in page_checks if item["is_prompt_page"]]
    return {
        "min_marker_pixels": min_marker_pixels,
        "min_non_white_ratio": min_non_white_ratio,
        "checked_pages": page_checks,
        "visual_marker_ok": all(item["marker_pixels_ok"] for item in marker_checks) and bool(marker_checks),
        "prompt_pages_ok": all(item["non_blank_ok"] for item in prompt_checks) and bool(prompt_pages),
        "render_non_blank_ok": all(item["non_blank_ok"] for item in page_checks),
    }


def verify_pdf_review(args: argparse.Namespace) -> None:
    pypdf = require("pypdf")
    pdfium = require("pypdfium2")
    case_dir = Path(args.case_dir).resolve()
    dirs = ensure_case_dirs(case_dir)
    pdf_path = Path(args.pdf).resolve()
    original = Path(args.original).resolve() if args.original else first_file(dirs["paper"], (".pdf",))
    applied_path = Path(args.applied).resolve() if args.applied else next(dirs["work"].glob("*_review_applied.json"), None)
    if not original:
        raise SystemExit("No original PDF found. Pass --original.")
    if not applied_path:
        raise SystemExit("No applied JSON found. Pass --applied.")
    applied_data = read_json(applied_path)
    original_pages = len(pypdf.PdfReader(str(original)).pages)
    reviewed_pages = len(pypdf.PdfReader(str(pdf_path)).pages)
    if isinstance(applied_data, list):
        applied = applied_data
        missing = [item for item in applied if item.get("status") == "missing"]
    else:
        applied = applied_data.get("applied", [])
        missing = applied_data.get("missing", [])
    issue_count = len(applied)
    expected_min_pages = original_pages + 1
    selected = sorted({int(item["page"]) for item in applied if item.get("status") == "applied"})
    selected += list(range(original_pages + 1, reviewed_pages + 1))
    selected = [page for page in selected if 1 <= page <= reviewed_pages]

    doc = pdfium.PdfDocument(str(pdf_path))
    rendered: list[Path] = []
    rendered_by_page: dict[int, Path] = {}
    key_dir = dirs["work"] / "reviewed_key_pages"
    key_dir.mkdir(parents=True, exist_ok=True)
    for page_number in selected[: args.max_pages]:
        image = doc[page_number - 1].render(scale=1.5).to_pil().convert("RGB")
        out = key_dir / f"page-{page_number:02d}.png"
        image.save(out, quality=90)
        rendered.append(out)
        rendered_by_page[page_number] = out
    sheet = dirs["work"] / f"{safe_stem(pdf_path)}_key_pages_contact_sheet.jpg"
    make_contact_sheet(rendered, sheet, args.cols, args.thumb_width)
    acceptance = build_pdf_render_acceptance(
        rendered_by_page,
        applied,
        original_pages,
        reviewed_pages,
        args.min_marker_pixels,
        args.min_non_white_ratio,
    )
    report = {
        "original_pages": original_pages,
        "reviewed_pages": reviewed_pages,
        "expected_min_pages": expected_min_pages,
        "issue_count": issue_count,
        "missing_count": len(missing),
        "contact_sheet": str(sheet),
        "page_count_ok": reviewed_pages >= expected_min_pages,
        "locator_count_ok": len(missing) == 0,
        "render_acceptance": acceptance,
        "render_acceptance_ok": acceptance["visual_marker_ok"] and acceptance["prompt_pages_ok"] and acceptance["render_non_blank_ok"],
    }
    write_json(dirs["work"] / f"{safe_stem(pdf_path)}_verification.json", report)
    write_json(dirs["work"] / "render_acceptance.json", acceptance)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def parse_exemplar_index(index_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = index_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or re.match(r"^\|\s*-+", stripped):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 7:
            continue
        sample_id, year, source_type, title, tags, keywords, card = cells[:7]
        if not sample_id or sample_id == "编号":
            continue
        rows.append(
            {
                "id": sample_id,
                "year": year,
                "source_type": source_type,
                "title": title,
                "tags": split_terms(tags),
                "keywords": split_terms(keywords),
                "card": card,
            }
        )
    return rows


def term_category(term: str) -> str:
    if term in PROBLEM_TAGS:
        return "problem"
    if term in METHOD_TAGS:
        return "method"
    if term in DATA_TAGS:
        return "data"
    if term in FIGURE_TAGS:
        return "figure"
    if term in WRITING_TAGS:
        return "writing"
    if term in RISK_TAGS:
        return "risk"
    return "other"


def score_weights(feedback_records: list[dict[str, Any]], target_terms: list[str]) -> dict[str, float]:
    weights: dict[str, float] = {
        "problem": 10.0,
        "method": 8.0,
        "data": 5.0,
        "figure": 4.0,
        "writing": 3.0,
        "other": 2.0,
        "keyword": 1.5,
        "topic": 3.0,
        "feedback_sample": 4.0,
        "feedback_context": 1.0,
        "risk_penalty": -6.0,
    }
    target_set = set(target_terms)
    related = [r for r in feedback_records if target_set.intersection(r.get("applicable_tags") or [])]
    for record in related[:8]:
        text = " ".join(str(record.get(key, "")) for key in ("scoring_implications", "positive_signals", "negative_signals"))
        if "同方法" in text or "方法" in text:
            weights["method"] += 0.5
        if "图" in text or "表" in text:
            weights["figure"] += 0.5
        if "数据" in text or "口径" in text:
            weights["data"] += 0.5
        if "结构" in text or "摘要" in text or "表达" in text:
            weights["writing"] += 0.5
    weights["method"] = min(weights["method"], 10.0)
    weights["figure"] = min(weights["figure"], 6.0)
    weights["data"] = min(weights["data"], 7.0)
    weights["writing"] = min(weights["writing"], 5.0)
    return weights


def load_feedback_log(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            records.append(item)
    return records


def feedback_hints_for_sample(sample: dict[str, Any], feedback_records: list[dict[str, Any]], target_terms: list[str]) -> tuple[float, list[str]]:
    target_set = set(target_terms)
    sample_id = sample["id"]
    sample_tags = set(sample.get("tags") or [])
    adjustment = 0.0
    hints: list[str] = []
    for record in feedback_records:
        applicable = set(record.get("applicable_tags") or [])
        if applicable and not (applicable & target_set or applicable & sample_tags):
            continue
        sample_feedback = str(record.get("sample_feedback", ""))
        implications = str(record.get("scoring_implications", ""))
        source = record.get("title") or record.get("authority") or "权威点评"
        if sample_id and sample_id in sample_feedback:
            if any(word in sample_feedback for word in ("帮助程度高", "强参考", "适合参考")):
                adjustment += 4.0
                hints.append(f"{source}: 明确提到 {sample_id} 可作为较强参考。")
            elif any(word in sample_feedback for word in ("帮助程度中", "可参考")):
                adjustment += 2.0
                hints.append(f"{source}: 提到 {sample_id} 可作为一般参考。")
            if any(word in sample_feedback for word in ("不适合", "不要照搬", "风险")):
                adjustment -= 4.0
                hints.append(f"{source}: 提醒 {sample_id} 存在不宜照搬处。")
        elif implications and applicable & target_set:
            hints.append(f"{source}: 对当前标签有校准提示，需人工判断是否适用。")
            adjustment += 0.5
        if len(hints) >= 3:
            break
    return adjustment, hints


def topic_terms(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[\s,，;；、/（）()]+", raw)
    return [p.strip() for p in parts if len(p.strip()) >= 2]


def score_exemplar(
    sample: dict[str, Any],
    target_terms: list[str],
    keyword_terms: list[str],
    topic: str,
    requested_risks: list[str],
    weights: dict[str, float],
    feedback_records: list[dict[str, Any]],
) -> dict[str, Any]:
    sample_tags = set(sample.get("tags") or [])
    sample_keywords = set(sample.get("keywords") or [])
    haystack = " ".join([sample.get("title", ""), " ".join(sample_tags), " ".join(sample_keywords)])
    score = 0.0
    breakdown: dict[str, float] = {}
    reasons: list[str] = []
    cautions: list[str] = []

    for term in target_terms:
        category = term_category(term)
        if category == "risk":
            continue
        hit = term in sample_tags or term in sample_keywords
        if hit:
            value = weights.get(category, weights["other"])
            score += value
            breakdown[category] = breakdown.get(category, 0.0) + value
            reasons.append(f"{term} 匹配{category}标签/关键词")

    for term in keyword_terms:
        if term in sample_keywords or term in haystack:
            value = weights["keyword"]
            score += value
            breakdown["keyword"] = breakdown.get("keyword", 0.0) + value
            reasons.append(f"关键词 {term} 命中")

    for term in topic_terms(topic):
        if term in haystack:
            value = weights["topic"]
            score += value
            breakdown["topic"] = breakdown.get("topic", 0.0) + value
            reasons.append(f"主题词 {term} 命中标题/关键词")

    sample_risks = sorted((sample_tags | sample_keywords) & RISK_TAGS)
    explicit_risk_overlap = sorted(set(requested_risks) & sample_tags)
    for risk in unique_terms(sample_risks, explicit_risk_overlap):
        penalty = abs(weights["risk_penalty"])
        score -= penalty
        breakdown["risk_penalty"] = breakdown.get("risk_penalty", 0.0) - penalty
        cautions.append(f"含风险标签：{risk}")

    if sample.get("source_type") == "image-folder" and "图像版论文" not in target_terms:
        score -= 1.0
        breakdown["image_source_penalty"] = breakdown.get("image_source_penalty", 0.0) - 1.0
        cautions.append("图片版样例可能只能学习卡片和视觉组织，需确认文本可读性")

    feedback_adjustment, feedback_hints = feedback_hints_for_sample(sample, feedback_records, target_terms)
    if feedback_adjustment:
        score += feedback_adjustment
        breakdown["feedback"] = round(feedback_adjustment, 2)

    if not reasons:
        reasons.append("无强标签命中，仅作为库规模不足时的低优先级候选")

    return {
        **sample,
        "score": round(score, 2),
        "score_breakdown": {k: round(v, 2) for k, v in breakdown.items()},
        "reasons": reasons[:8],
        "cautions": cautions[:6],
        "feedback_hints": feedback_hints,
    }


def recommended_use(item: dict[str, Any]) -> str:
    tags = set(item.get("tags") or [])
    if tags & {"图表密集", "图表组织好", "流程图", "模型结构图"}:
        return "优先参考图表组织、模型路线呈现和正文引用方式。"
    if tags & {"优化", "动态规划", "线性规划", "非线性规划", "整数规划"}:
        return "优先参考优化模型变量、目标函数、约束和求解过程写法。"
    if tags & {"回归分析", "统计分析", "聚类", "机器学习"}:
        return "优先参考数据处理、指标解释、检验和结果讨论方式。"
    if tags & {"仿真", "蒙特卡洛", "微分方程"}:
        return "优先参考仿真过程、参数说明和结果验证写法。"
    return "优先参考结构安排和摘要级表达，不复制具体内容。"


def write_exemplar_match_report(out: Path, data: dict[str, Any]) -> None:
    lines = [
        "# 本地样例匹配报告",
        "",
        f"- 生成时间：{data['generated_at']}",
        f"- 样例索引：{data['index']}",
        f"- 待审标签：{', '.join(data['inputs']['labels']) or '未提供'}",
        f"- 方法标签：{', '.join(data['inputs']['methods']) or '未提供'}",
        f"- 主题：{data['inputs']['topic'] or '未提供'}",
        f"- 历史反馈记录：{data['feedback']['record_count']} 条；本次命中上下文：{data['feedback']['related_count']} 条",
        "",
        "## 使用边界",
        "",
        "- 分数只用于排序和解释，不是论文质量分。",
        "- 本地样例只用于学习写法、结构和图表组织，不复制内容、数据或结论。",
        "- 正式审稿仍必须运行 `search-references` 联网检索权威资料。",
        "- 历史点评只作为轻量校准信号，不因单条记录直接改写评分标准。",
        "",
        "## 候选样例",
        "",
        "| 排名 | 编号 | 分数 | 年份 | 标题 | 选择理由 | 风险提示 | 卡片 |",
        "|---:|---|---:|---:|---|---|---|---|",
    ]
    for rank, item in enumerate(data["candidates"], 1):
        title = (item.get("title") or "").replace("|", "\\|")
        reason = "；".join(item.get("reasons") or [])[:160].replace("|", "\\|")
        caution = "；".join(item.get("cautions") or [])[:120].replace("|", "\\|")
        lines.append(f"| {rank} | {item['id']} | {item['score']} | {item.get('year', '')} | {title} | {reason} | {caution} | {item.get('card', '')} |")
    lines.extend(["", "## 核心样例", ""])
    for rank, item in enumerate(data["core"], 1):
        lines.extend(
            [
                f"### {rank}. {item['id']} {item.get('title', '')}",
                "",
                f"- 分数：{item['score']}",
                f"- 标签：{', '.join(item.get('tags') or [])}",
                f"- 关键词：{', '.join((item.get('keywords') or [])[:12])}",
                f"- 建议用途：{item.get('recommended_use')}",
                f"- 选择理由：{'；'.join(item.get('reasons') or [])}",
                f"- 风险提示：{'；'.join(item.get('cautions') or []) or '无明显索引风险标签'}",
                f"- 反馈提示：{'；'.join(item.get('feedback_hints') or []) or '无直接历史反馈命中'}",
                f"- 卡片：{item.get('card', '')}",
                "",
            ]
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def match_exemplars(args: argparse.Namespace) -> None:
    case_dir = Path(args.case_dir).resolve() if args.case_dir else None
    work = case_dir / "work" if case_dir else repo_root() / "math-modeling-review-cases" / "_exemplar-match"
    index_path = Path(args.index).resolve() if args.index else repo_root() / ".agents" / "skills" / "13-cumcm-paper-review" / "references" / "exemplars" / "index.md"
    if not index_path.exists():
        raise SystemExit(f"Exemplar index not found: {index_path}")
    samples = parse_exemplar_index(index_path)
    if not samples:
        raise SystemExit(f"No exemplar rows found in: {index_path}")

    labels = split_terms(args.labels)
    methods = split_terms(args.methods)
    data_tags = split_terms(args.data_tags)
    figure_tags = split_terms(args.figure_tags)
    writing_tags = split_terms(args.writing_tags)
    risk_tags = split_terms(args.risk_tags)
    keywords = split_terms(args.keywords)
    target_terms = unique_terms(labels, methods, data_tags, figure_tags, writing_tags)

    feedback_log = Path(args.feedback_log).resolve() if args.feedback_log else repo_root() / "math-modeling-review-cases" / "_learning" / "exemplar_feedback_log.jsonl"
    feedback_records = [] if args.no_feedback else load_feedback_log(feedback_log)
    related_feedback = [r for r in feedback_records if set(r.get("applicable_tags") or []) & set(target_terms)]
    weights = score_weights(feedback_records, target_terms)
    scored = [
        score_exemplar(sample, target_terms, keywords, args.topic or "", risk_tags, weights, feedback_records)
        for sample in samples
    ]
    scored.sort(key=lambda item: (item["score"], item.get("year", ""), item.get("id", "")), reverse=True)

    candidate_count = max(1, min(args.candidates, len(scored)))
    core_count = max(1, min(args.core, candidate_count))
    candidates = scored[:candidate_count]
    core = [dict(item, recommended_use=recommended_use(item)) for item in candidates[:core_count]]
    for item in candidates:
        item["recommended_use"] = recommended_use(item)

    data = {
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "index": str(index_path),
        "inputs": {
            "labels": labels,
            "methods": methods,
            "data_tags": data_tags,
            "figure_tags": figure_tags,
            "writing_tags": writing_tags,
            "risk_tags": risk_tags,
            "keywords": keywords,
            "topic": args.topic or "",
        },
        "weights": weights,
        "feedback": {
            "log": str(feedback_log),
            "enabled": not args.no_feedback,
            "record_count": len(feedback_records),
            "related_count": len(related_feedback),
        },
        "sample_count": len(samples),
        "candidates": candidates,
        "core": core,
        "next_step": "正式审稿还必须运行 search-references，外部权威资料检索不能由本地样例匹配替代。",
    }
    out = Path(args.out).resolve() if args.out else work / "exemplar_match.json"
    report = Path(args.report).resolve() if args.report else work / "exemplar_match_report.md"
    write_json(out, data)
    write_exemplar_match_report(report, data)
    result = {
        "json": str(out),
        "report": str(report),
        "sample_count": len(samples),
        "candidate_count": len(candidates),
        "core_count": len(core),
        "related_feedback": len(related_feedback),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def build_external_queries(args: argparse.Namespace) -> list[str]:
    labels = split_terms(args.labels)
    methods = split_terms(args.methods)
    topic = (args.topic or "").strip()
    problem_summary = (args.problem_summary or "").strip()
    label_text = ", ".join(labels[:8]) or "数学建模论文审阅"
    method_text = ", ".join(methods[:6]) or "建模方法, 模型检验, 图表表达"
    topic_text = topic or problem_summary or label_text
    queries = [
        f"权威 全国大学生数学建模竞赛 优秀论文 {topic_text} {method_text} 摘要 模型 检验 图表",
        f"academic paper or review about {topic_text} using {method_text} validation metrics figures tables",
        f"textbook official documentation {method_text} model validation sensitivity analysis reproducibility",
        f"mathematical modeling competition paper {label_text} structure abstract figures appendix references",
    ]
    return list(dict.fromkeys(q.strip() for q in queries if q.strip()))


def parse_exa_output(text: str, query: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for block in re.split(r"\n(?=Title:\s)", text.strip()):
        if not block.strip():
            continue
        fields: dict[str, str] = {}
        current: str | None = None
        highlight_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("Title:"):
                fields["title"] = line.split(":", 1)[1].strip()
                current = "title"
            elif line.startswith("URL:"):
                fields["url"] = line.split(":", 1)[1].strip()
                current = "url"
            elif line.startswith("Published:"):
                fields["published"] = line.split(":", 1)[1].strip()
                current = "published"
            elif line.startswith("Author:"):
                fields["author"] = line.split(":", 1)[1].strip()
                current = "author"
            elif line.startswith("Highlights:"):
                current = "highlights"
            elif current == "highlights":
                highlight_lines.append(line)
        url = fields.get("url", "")
        if not url:
            continue
        domain = urlparse(url).netloc.lower()
        results.append(
            {
                "query": query,
                "title": fields.get("title", ""),
                "url": url,
                "published": fields.get("published", ""),
                "author": fields.get("author", ""),
                "domain": domain,
                "source_type": classify_source_type(domain, fields.get("title", "")),
                "credibility": estimate_credibility(domain, fields.get("title", "")),
                "highlights": clean_highlights("\n".join(highlight_lines)),
            }
        )
    return results


def clean_highlights(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip() != "---"]
    return "\n".join(lines).strip()


def classify_source_type(domain: str, title: str) -> str:
    text = f"{domain} {title}".lower()
    if "github.com" in domain:
        return "工具/代码资料"
    if any(x in text for x in ["arxiv", "doi.org", "ieee", "springer", "sciencedirect", "researchgate", "mdpi", "frontiers", "hanspub", "journal"]):
        return "学术论文/论文页面"
    if any(x in text for x in ["cumcm", "cmathc", "mcm.edu", "竞赛", "数学建模", "优秀论文"]):
        return "数模论文/竞赛资料"
    if domain.endswith(".edu") or ".edu." in domain or domain.endswith(".gov") or ".gov." in domain:
        return "官方/高校资料"
    return "网页资料"


def estimate_credibility(domain: str, title: str) -> str:
    text = f"{domain} {title}".lower()
    high_markers = ["cumcm", "cmathc", "mcm.edu", "arxiv", "doi.org", "ieee", "springer", "sciencedirect", ".edu", ".gov"]
    medium_markers = ["github.com", "researchgate", "mdpi", "frontiers", "cnki", "wanfang", "hanspub", "journal", "高校", "university"]
    if any(marker in text for marker in high_markers):
        return "高"
    if any(marker in text for marker in medium_markers):
        return "中"
    return "待核验"


def call_exa(query: str, num_results: int, mcporter: str) -> list[dict[str, Any]]:
    cmd = [mcporter, "call", "exa.web_search_exa", f"query={query}", f"numResults={num_results}"]
    proc = subprocess.run(
        cmd,
        cwd=repo_root(),
        env=tool_env(),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"Exa search failed for query: {query}\n{proc.stderr.strip() or proc.stdout.strip()}")
    return parse_exa_output(proc.stdout, query)


def write_external_cards(records: list[dict[str, Any]], cards_dir: Path, today: str) -> list[str]:
    cards_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for idx, item in enumerate(records, 1):
        domain_slug = slug_text(item.get("domain") or "source")
        card_id = f"EXT-{today[:4]}-{domain_slug}-{idx:02d}"
        path = cards_dir / f"{card_id}.card.md"
        summary = item.get("highlights", "").strip()
        if len(summary) > 900:
            summary = summary[:900].rstrip() + "..."
        content = "\n".join(
            [
                f"# 外部参考编号：{card_id}",
                "",
                f"- 来源类型：{item.get('source_type', '网页资料')}",
                f"- 题名：{item.get('title', '')}",
                f"- 作者/机构：{item.get('author', '')}",
                f"- 年份：{item.get('published', '')}",
                f"- 链接：{item.get('url', '')}",
                f"- 检索日期：{today}",
                f"- 可信度：{item.get('credibility', '待核验')}",
                "- 题型标签：待审稿时补充",
                "- 方法标签：待审稿时补充",
                "- 数据标签：待审稿时补充",
                "- 写法标签：待审稿时补充",
                "- 图表标签：待审稿时补充",
                "- 适合参考：待人工/审稿判断确认",
                "- 不适合参考：不得复制正文、数据、图表或结论",
                f"- 摘要级总结：{summary}",
                "- 关键词：待审稿时补充",
                "",
            ]
        )
        path.write_text(content, encoding="utf-8")
        written.append(str(path))
    return written


def write_external_report(out: Path, data: dict[str, Any]) -> None:
    lines = [
        "# 外部权威资料检索报告",
        "",
        f"- 生成时间：{data['generated_at']}",
        f"- 标签：{', '.join(data.get('labels') or []) or '未提供'}",
        f"- 方法：{', '.join(data.get('methods') or []) or '未提供'}",
        f"- 主题：{data.get('topic') or '未提供'}",
        "",
        "## 检索词",
        "",
    ]
    for query in data["queries"]:
        lines.append(f"- {query}")
    lines.extend(["", "## 候选资料", "", "| 序号 | 可信度 | 来源类型 | 标题 | 来源 | 用途初判 |", "|---:|---|---|---|---|---|"])
    for idx, item in enumerate(data["candidates"], 1):
        title = (item.get("title") or "").replace("|", "\\|")
        domain = item.get("domain") or ""
        lines.append(f"| {idx} | {item.get('credibility')} | {item.get('source_type')} | [{title}]({item.get('url')}) | {domain} | 待审稿时确认支撑何种判断 |")
    lines.extend(
        [
            "",
            "## 使用规则",
            "",
            "- 只把这些资料作为方法核验、写法对标和图表表达参考。",
            "- 可信度是来源初筛，不等于内容必然正确；正式批注前还要核对题目、论文上下文和数据条件。",
            "- 无法确认数据、代码或统计口径时，在审稿批注中标为“需确认”。",
            "- 不复制外部资料正文、图表、数据或结论。",
            "",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def search_references(args: argparse.Namespace) -> None:
    case_dir = Path(args.case_dir).resolve() if args.case_dir else None
    work = case_dir / "work" if case_dir else repo_root() / "math-modeling-review-cases" / "_external-search"
    today = _dt.date.today().isoformat()
    queries = build_external_queries(args)
    labels = split_terms(args.labels)
    methods = split_terms(args.methods)
    candidates: list[dict[str, Any]] = []
    if not args.dry_run:
        mcporter = resolve_tool("mcporter", args.mcporter)
        seen_urls: set[str] = set()
        for query in queries:
            for item in call_exa(query, args.num_results, mcporter):
                url = item.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    candidates.append(item)
                if len(candidates) >= args.max_candidates:
                    break
            if len(candidates) >= args.max_candidates:
                break
    data = {
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "search_backend": "agent-reach search route via mcporter + Exa MCP",
        "labels": labels,
        "methods": methods,
        "topic": args.topic or "",
        "problem_summary": args.problem_summary or "",
        "queries": queries,
        "dry_run": bool(args.dry_run),
        "candidates": candidates,
    }
    out = Path(args.out).resolve() if args.out else work / "external_references.json"
    report = Path(args.report).resolve() if args.report else work / "external_reference_report.md"
    write_json(out, data)
    write_external_report(report, data)
    card_paths: list[str] = []
    if not args.no_cards and candidates:
        cards_dir = Path(args.cards_dir).resolve() if args.cards_dir else work / "external-reference-cards"
        card_paths = write_external_cards(candidates, cards_dir, today)
    result = {"json": str(out), "report": str(report), "cards": card_paths, "candidate_count": len(candidates)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


def read_json_if_exists(path: Path) -> Any | None:
    if not path.exists():
        return None
    return read_json(path)


def one_line(value: Any, limit: int = 120) -> str:
    text = str(value or "").replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def guess_reference_use(item: dict[str, Any]) -> str:
    text = " ".join(
        str(item.get(key, ""))
        for key in ("title", "source_type", "highlights", "domain")
    ).lower()
    uses: list[str] = []
    if any(word in text for word in ["validation", "检验", "sensitivity", "敏感", "reproduc", "显著性", "残差"]):
        uses.append("支撑模型检验、敏感性分析或可复现性建议")
    if any(word in text for word in ["figure", "table", "图", "表", "visual", "chart"]):
        uses.append("支撑图表表达和结果呈现建议")
    if any(word in text for word in ["textbook", "official", "documentation", "教材", "官方"]):
        uses.append("支撑方法流程、术语和规范性核验")
    if any(word in text for word in ["competition", "cumcm", "mcm", "优秀论文", "数学建模"]):
        uses.append("支撑竞赛论文结构、摘要和附录组织对标")
    if any(word in text for word in ["paper", "review", "arxiv", "doi", "journal", "论文", "综述"]):
        uses.append("支撑方法适配性、指标定义或结果讨论核验")
    return "；".join(dict.fromkeys(uses)) or "待审稿时结合具体批注确认用途"


def load_reference_sources(case_dir: Path, args: argparse.Namespace) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    work = case_dir / "work"
    exemplar_path = Path(args.exemplar_match).resolve() if args.exemplar_match else work / "exemplar_match.json"
    external_path = Path(args.external_refs).resolve() if args.external_refs else work / "external_references.json"
    return read_json_if_exists(exemplar_path), read_json_if_exists(external_path)


def collect_confirmation_items(case_dir: Path, args: argparse.Namespace) -> list[dict[str, str]]:
    work = case_dir / "work"
    items: list[dict[str, str]] = []
    issue_paths: list[Path] = []
    if args.issues:
        issue_paths.append(Path(args.issues).resolve())
    else:
        issue_paths.extend(path for path in [work / "issues.json", work / "figure_issues.json"] if path.exists())
    for path in issue_paths:
        data = read_json_if_exists(path)
        if not isinstance(data, list):
            continue
        for issue in data:
            message = str(issue.get("message", ""))
            target = issue.get("target") or issue.get("search") or issue.get("id") or ""
            if "需确认" in message or "请提供" in message or "原始数据" in message or "脚本" in message:
                items.append(
                    {
                        "source_file": str(path),
                        "location": one_line(target, 80),
                        "type": str(issue.get("type", "需确认")),
                        "needed": one_line(message, 180),
                    }
                )

    figure_path = Path(args.figure_review).resolve() if args.figure_review else work / "figure_review.json"
    data = read_json_if_exists(figure_path)
    if isinstance(data, list):
        for record in data:
            need = record.get("needs_confirmation")
            if need:
                location = record.get("title") or record.get("search") or record.get("id") or ""
                items.append(
                    {
                        "source_file": str(figure_path),
                        "location": one_line(location, 80),
                        "type": "图表数据需确认",
                        "needed": one_line(need, 180),
                    }
                )
    return items


def write_reference_report(out: Path, data: dict[str, Any]) -> None:
    exemplar = data.get("exemplar_match") or {}
    external = data.get("external_references") or {}
    core = exemplar.get("core") or []
    candidates = exemplar.get("candidates") or []
    ext_candidates = external.get("candidates") or []
    confirmation_items = data.get("confirmation_items") or []
    lines = [
        "# 参考来源报告",
        "",
        f"- 生成时间：{data['generated_at']}",
        f"- Case：{data['case_dir']}",
        "",
        "## 本地样例读取情况",
        "",
    ]
    if core:
        lines.extend(["| 编号 | 标题 | 读取范围 | 用途 | 风险提示 | 卡片 |", "|---|---|---|---|---|---|"])
        for item in core:
            title = one_line(item.get("title", ""), 80).replace("|", "\\|")
            use = one_line(item.get("recommended_use") or "结构、写法和图表组织参考", 120).replace("|", "\\|")
            caution = one_line("；".join(item.get("cautions") or []), 100).replace("|", "\\|")
            card = item.get("card", "")
            lines.append(f"| {item.get('id', '')} | {title} | 样例卡片/必要片段 | {use} | {caution or '无明显索引风险'} | {card} |")
    elif candidates:
        lines.extend(["未选出核心样例；以下仅为候选样例，审稿时不得声称已精读全文。", ""])
        for item in candidates[:8]:
            lines.append(f"- {item.get('id', '')}：{one_line(item.get('title', ''), 100)}")
    else:
        lines.append("- 未找到 `exemplar_match.json` 或未生成本地样例匹配结果。")

    lines.extend(["", "## 外部资料检索情况", ""])
    if external:
        lines.append(f"- 检索后端：{external.get('search_backend', '未记录')}")
        lines.append(f"- 检索日期：{external.get('generated_at', '未记录')}")
        lines.append(f"- 是否 dry-run：{external.get('dry_run', False)}")
        lines.append("")
    if ext_candidates:
        lines.extend(["| 序号 | 可信度 | 来源类型 | 标题 | 来源 | 支撑建议/用途 |", "|---:|---|---|---|---|---|"])
        for idx, item in enumerate(ext_candidates, 1):
            title = one_line(item.get("title", ""), 90).replace("|", "\\|")
            domain = item.get("domain") or ""
            url = item.get("url") or ""
            source = f"[{domain}]({url})" if url else domain
            use = one_line(item.get("supports") or guess_reference_use(item), 140).replace("|", "\\|")
            lines.append(f"| {idx} | {item.get('credibility', '待核验')} | {item.get('source_type', '')} | {title} | {source} | {use} |")
    else:
        lines.append("- 未找到外部资料候选。正式审稿如未联网检索，必须在交付中说明可靠性限制。")

    lines.extend(["", "## 资料到建议的使用边界", ""])
    lines.extend(
        [
            "- 本地样例只支撑写法、结构、图表组织和表达风格参考，不支撑照搬数据、结论或模型参数。",
            "- 外部资料的可信度是来源初筛，不等于内容自动正确；正式批注前仍需核对题目、论文上下文和数据条件。",
            "- 若资料用途显示为“待确认”，需要审稿者在具体批注中手动说明该资料支撑哪条判断。",
            "",
            "## 仍需用户提供数据确认的判断",
            "",
        ]
    )
    if confirmation_items:
        lines.extend(["| 序号 | 位置 | 类型 | 需用户提供 | 来源记录 |", "|---:|---|---|---|---|"])
        for idx, item in enumerate(confirmation_items, 1):
            location = item["location"].replace("|", "\\|")
            needed = item["needed"].replace("|", "\\|")
            lines.append(f"| {idx} | {location or '未记录'} | {item['type']} | {needed} | {item['source_file']} |")
    else:
        lines.append("- 当前结构化记录中未发现“需确认”项；若审稿过程中无法核验图表数据、统计口径或模型输出，应先补入 `issues.json` 或 `figure_review.json` 后重新生成。")
    lines.extend(
        [
            "",
            "## 生成依据",
            "",
            f"- 本地样例匹配文件：{data.get('exemplar_match_path')}",
            f"- 外部资料检索文件：{data.get('external_refs_path')}",
            f"- 审稿意见文件：{', '.join(data.get('issue_paths') or []) or '未找到'}",
            f"- 图审记录文件：{data.get('figure_review_path') or '未找到'}",
            "",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def build_reference_report(args: argparse.Namespace) -> None:
    case_dir = Path(args.case_dir).resolve()
    work = case_dir / "work"
    work.mkdir(parents=True, exist_ok=True)
    exemplar, external = load_reference_sources(case_dir, args)
    confirmation_items = collect_confirmation_items(case_dir, args)
    exemplar_path = Path(args.exemplar_match).resolve() if args.exemplar_match else work / "exemplar_match.json"
    external_path = Path(args.external_refs).resolve() if args.external_refs else work / "external_references.json"
    issue_paths = []
    if args.issues:
        issue_paths.append(str(Path(args.issues).resolve()))
    else:
        issue_paths.extend(str(path) for path in [work / "issues.json", work / "figure_issues.json"] if path.exists())
    figure_path = Path(args.figure_review).resolve() if args.figure_review else work / "figure_review.json"
    data = {
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "case_dir": str(case_dir),
        "exemplar_match_path": str(exemplar_path),
        "external_refs_path": str(external_path),
        "issue_paths": issue_paths,
        "figure_review_path": str(figure_path) if figure_path.exists() else "",
        "exemplar_match": exemplar or {},
        "external_references": external or {},
        "confirmation_items": confirmation_items,
    }
    out = Path(args.out).resolve() if args.out else work / "reference_report.md"
    json_out = Path(args.json_out).resolve() if args.json_out else work / "reference_report.json"
    write_reference_report(out, data)
    write_json(json_out, data)
    result = {
        "report": str(out),
        "json": str(json_out),
        "local_core_count": len((exemplar or {}).get("core") or []),
        "external_count": len((external or {}).get("candidates") or []),
        "confirmation_count": len(confirmation_items),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


REGRESSION_CASES = [
    {
        "id": "A229",
        "fixture": "pdf-markup",
        "real_case": "2018 Problem A paper PDF trial",
        "guards": ["PDF visible outline markers", "appended prompt pages", "applied locator JSON"],
    },
    {
        "id": "B203",
        "fixture": "docx-highlight",
        "real_case": "2018 Problem B DOCX trial",
        "guards": ["DOCX yellow source highlight", "blue visible prompt paragraph", "review notes"],
    },
    {
        "id": "C008",
        "fixture": "figure-json",
        "real_case": "2018 Problem C PDF figure-review trial",
        "guards": ["figure_review.json", "figure_issues.json", "needs_confirmation propagation"],
    },
    {
        "id": "FIGINV",
        "fixture": "figure-inventory",
        "real_case": "PDF/DOCX figure inventory before formal figure review",
        "guards": ["figure_inventory.json", "caption extraction", "DOCX media/caption scan"],
    },
]


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def make_minimal_docx(path: Path) -> None:
    docx = require("docx")
    doc = docx.Document()
    doc.add_heading("B203 回归测试论文", level=1)
    doc.add_paragraph("摘要：本文用于测试 DOCX 高亮和可见提示段。")
    doc.add_paragraph("B203 定位段落：会员消费结构需要补充验证。")
    doc.add_paragraph("图 1 DOCX 图表清单测试图")
    doc.add_paragraph("结论：测试结束。")
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))


def make_minimal_pdf(path: Path) -> None:
    canvas = require("reportlab.pdfgen.canvas")
    pdfmetrics = require("reportlab.pdfbase.pdfmetrics")
    cidfonts = require("reportlab.pdfbase.cidfonts")
    UnicodeCIDFont = cidfonts.UnicodeCIDFont
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        font_name = "STSong-Light"
    except Exception:
        font_name = "Helvetica"
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=(595.2756, 841.8898))
    c.setFont(font_name, 14)
    c.drawString(72, 760, "A229 回归测试 PDF")
    c.setFont(font_name, 11)
    c.drawString(72, 700, "图 1 测试趋势图：该处需要可见描边标注。")
    c.drawString(72, 675, "正文说明：图 1 用于测试 PDF 标注和提示页。")
    c.showPage()
    c.save()


def regression_docx_highlight(root: Path) -> dict[str, Any]:
    case_dir = root / "B203-docx-highlight"
    dirs = ensure_case_dirs(case_dir)
    docx_path = dirs["paper"] / "B203_minimal.docx"
    make_minimal_docx(docx_path)
    issues_path = dirs["work"] / "issues.json"
    write_json(
        issues_path,
        [
            {
                "target": "B203 定位段落：会员消费结构需要补充验证。",
                "type": "需确认",
                "message": "请补充会员消费结构的原始统计口径和计算脚本。",
            }
        ],
    )
    write_docx_review(
        argparse.Namespace(
            case_dir=str(case_dir),
            issues=str(issues_path),
            src=None,
            out=None,
            labels="回归测试,DOCX",
            references="B203 fixture",
        )
    )
    reviewed = dirs["reviewed"] / "B203_minimal_reviewed.docx"
    applied = read_json(dirs["work"] / "B203_minimal_docx_review_applied.json")
    assert_condition(reviewed.exists(), "DOCX reviewed file was not created")
    assert_condition(len(applied.get("applied", [])) == 1, "DOCX issue was not applied")
    assert_condition(len(applied.get("missing", [])) == 0, "DOCX issue unexpectedly missing")
    with zipfile.ZipFile(reviewed) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
    assert_condition("w:highlight" in document_xml, "DOCX highlight marker missing")
    assert_condition("审阅提示" in document_xml, "DOCX visible prompt text missing")
    return {"case": "B203", "status": "passed", "reviewed": str(reviewed)}


def regression_pdf_markup(root: Path) -> dict[str, Any]:
    pypdf = require("pypdf")
    case_dir = root / "A229-pdf-markup"
    dirs = ensure_case_dirs(case_dir)
    pdf_path = dirs["paper"] / "A229_minimal.pdf"
    make_minimal_pdf(pdf_path)
    issues_path = dirs["work"] / "issues.json"
    write_json(
        issues_path,
        [
            {
                "page": 1,
                "target": "图 1 测试趋势图",
                "type": "图表建议",
                "message": "建议检查图题、正文引用和数据口径，并保持 WPS 可见标注。",
                "bbox": [70, 130, 315, 155],
                "color": "blue",
            }
        ],
    )
    write_pdf_review(
        argparse.Namespace(
            case_dir=str(case_dir),
            issues=str(issues_path),
            src=None,
            out=None,
            labels="回归测试,PDF",
            references="A229 fixture",
        )
    )
    reviewed = dirs["reviewed"] / "A229_minimal_reviewed.pdf"
    applied = read_json(dirs["work"] / "A229_minimal_review_applied.json")
    reader = pypdf.PdfReader(str(reviewed))
    assert_condition(reviewed.exists(), "PDF reviewed file was not created")
    assert_condition(len(reader.pages) >= 2, "PDF prompt page was not appended")
    assert_condition(len(applied.get("missing", [])) == 0, "PDF issue unexpectedly missing")
    assert_condition(any(item.get("status") == "applied" for item in applied.get("applied", [])), "PDF issue was not applied")
    verify_pdf_review(
        argparse.Namespace(
            case_dir=str(case_dir),
            pdf=str(reviewed),
            original=None,
            applied=None,
            max_pages=24,
            cols=4,
            thumb_width=360,
            min_marker_pixels=30,
            min_non_white_ratio=0.001,
        )
    )
    verification = read_json(dirs["work"] / "A229_minimal_reviewed_verification.json")
    assert_condition(verification.get("render_acceptance_ok"), "PDF render acceptance failed")
    return {
        "case": "A229",
        "status": "passed",
        "reviewed": str(reviewed),
        "pages": len(reader.pages),
        "render_acceptance": str(dirs["work"] / "render_acceptance.json"),
    }


def regression_figure_inventory(root: Path) -> dict[str, Any]:
    pdf_case = root / "figure-inventory-pdf"
    pdf_dirs = ensure_case_dirs(pdf_case)
    make_minimal_pdf(pdf_dirs["paper"] / "inventory_minimal.pdf")
    build_figure_inventory(
        argparse.Namespace(
            case_dir=str(pdf_case),
            file=None,
            format="pdf",
            out=None,
            md_out=None,
        )
    )
    pdf_inventory = read_json(pdf_dirs["work"] / "figure_inventory.json")
    pdf_records = pdf_inventory.get("records", [])
    assert_condition(any(record.get("title", "").startswith("图 1") for record in pdf_records), "PDF figure caption was not inventoried")

    docx_case = root / "figure-inventory-docx"
    docx_dirs = ensure_case_dirs(docx_case)
    make_minimal_docx(docx_dirs["paper"] / "inventory_minimal.docx")
    build_figure_inventory(
        argparse.Namespace(
            case_dir=str(docx_case),
            file=None,
            format="docx",
            out=None,
            md_out=None,
        )
    )
    docx_inventory = read_json(docx_dirs["work"] / "figure_inventory.json")
    docx_records = docx_inventory.get("records", [])
    assert_condition(any(record.get("title", "").startswith("图 1") for record in docx_records), "DOCX figure caption was not inventoried")
    return {
        "case": "figure_inventory",
        "status": "passed",
        "pdf_records": len(pdf_records),
        "docx_records": len(docx_records),
    }


def regression_figure_json(root: Path) -> dict[str, Any]:
    case_dir = root / "C008-figure-json"
    dirs = ensure_case_dirs(case_dir)
    draft = dirs["work"] / "pdf_figure_review_draft.md"
    draft.write_text(
        """# Figure Review Draft

---
id: fig-001
page: 1
search: 图 1 聚类结果
bbox:
title: 图 1 聚类结果
visual_type: 数据分布图
context_position: 结果分析小节
body_claim: 正文声称聚类分组能支撑用户分类
visual_observation: 图中只有类别散点，没有样本量和坐标单位
evidence_judgment: 无法判断
data_traceability: 未说明聚类输入变量、标准化方法和 K 值选择
needs_confirmation: 聚类原始数据、标准化脚本、K 值选择依据和各类样本数
content_advice: 补充分组统计表和 K 值选择依据
style_advice: 增大字号，标明坐标轴含义，保证黑白打印可辨
color: blue
---
""",
        encoding="utf-8",
    )
    build_figure_issues(
        argparse.Namespace(
            format="pdf",
            draft=str(draft),
            case_dir=str(case_dir),
            out=None,
            records_out=None,
        )
    )
    records = read_json(dirs["work"] / "figure_review.json")
    issues = read_json(dirs["work"] / "figure_issues.json")
    assert_condition(len(records) == 1, "figure_review.json should contain one record")
    assert_condition(len(issues) == 1, "figure_issues.json should contain one issue")
    assert_condition(issues[0].get("type") == "需确认", "figure issue should propagate needs_confirmation")
    assert_condition("请提供" in issues[0].get("message", ""), "figure issue should request confirmation materials")
    return {"case": "C008", "status": "passed", "records": str(dirs["work"] / "figure_review.json")}


def regression_reference_report(root: Path) -> dict[str, Any]:
    case_dir = root / "reference-report"
    dirs = ensure_case_dirs(case_dir)
    write_json(
        dirs["work"] / "exemplar_match.json",
        {
            "core": [
                {
                    "id": "B203",
                    "title": "B203 DOCX 高亮回归样例",
                    "recommended_use": "验证 DOCX 高亮和可见提示段。",
                    "cautions": [],
                    "card": "regression/B203.card.md",
                }
            ],
            "candidates": [],
        },
    )
    write_json(
        dirs["work"] / "external_references.json",
        {
            "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "search_backend": "regression fixture",
            "dry_run": False,
            "candidates": [
                {
                    "title": "Model validation and figures regression source",
                    "url": "https://example.org/model-validation",
                    "domain": "example.org",
                    "source_type": "学术论文/论文页面",
                    "credibility": "待核验",
                    "highlights": "validation metrics figures tables",
                }
            ],
        },
    )
    write_json(
        dirs["work"] / "issues.json",
        [
            {
                "target": "图 1 聚类结果",
                "type": "需确认",
                "message": "需确认：请提供聚类原始数据和生成脚本。",
            }
        ],
    )
    build_reference_report(
        argparse.Namespace(
            case_dir=str(case_dir),
            exemplar_match=None,
            external_refs=None,
            issues=None,
            figure_review=None,
            out=None,
            json_out=None,
        )
    )
    report = dirs["work"] / "reference_report.md"
    text = report.read_text(encoding="utf-8")
    assert_condition("本地样例读取情况" in text, "reference report missing local exemplar section")
    assert_condition("外部资料检索情况" in text, "reference report missing external reference section")
    assert_condition("仍需用户提供数据确认" in text, "reference report missing confirmation section")
    assert_condition("聚类原始数据" in text, "reference report missing confirmation detail")
    return {"case": "reference_report", "status": "passed", "report": str(report)}


def write_regression_manifest(out: Path, run_results: list[dict[str, Any]]) -> None:
    data = {
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "source_cases": REGRESSION_CASES,
        "results": run_results,
    }
    write_json(out, data)


def run_regression_tests(args: argparse.Namespace) -> None:
    root = Path(args.run_dir).resolve() if args.run_dir else repo_root() / "math-modeling-review-cases" / "_regression" / _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    root.mkdir(parents=True, exist_ok=True)
    tests = [
        regression_docx_highlight,
        regression_pdf_markup,
        regression_figure_inventory,
        regression_figure_json,
        regression_reference_report,
    ]
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for test in tests:
        try:
            results.append(test(root))
        except Exception as exc:
            failures.append({"test": test.__name__, "error": str(exc)})
            if args.fail_fast:
                break
    manifest = root / "regression_manifest.json"
    write_regression_manifest(manifest, results)
    summary = {
        "run_dir": str(root),
        "manifest": str(manifest),
        "passed": len(results),
        "failed": len(failures),
        "failures": failures,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(2)


def feedback_template() -> str:
    return """# Exemplar Feedback Draft

说明：每条权威点评记录用 --- 分隔。来源可以是视频、文档、网页、讲座、教师评语或赛后点评。
只记录点评者观点和可迁移评价标准，不复制受版权保护的长段内容。

---
source_type: 视频/文档/网页/讲座/教师评语/赛后点评
title: 权威点评资料标题
source_url:
source_path:
authority: 机构/老师/专家/竞赛组委会/课程
authority_level: 高/中/待核验
review_date: YYYY-MM-DD
related_problem: 赛题年份、题号或主题
applicable_tags: 优化, 图表密集, 模型检验
useful_for: 摘要, 模型建立, 模型求解, 图表, 检验, 语言, 格式
positive_signals: |
  点评中明确认为好的写法、结构、图表或论证特征。
negative_signals: |
  点评中明确批评的问题、扣分点或不应学习的特征。
sample_feedback: |
  如果点评涉及具体样例，记录样例编号、帮助程度高/中/低、适合参考处和不适合参考处。
scoring_implications: |
  对后续样例匹配权重的启发，例如“同方法比同年份更重要”“图审场景提高图表标签权重”。
limitations: |
  该点评适用范围和不能外推的地方。
---
"""


def make_feedback_template(args: argparse.Namespace) -> None:
    case_dir = Path(args.case_dir).resolve() if args.case_dir else None
    out = Path(args.out).resolve() if args.out else None
    if out is None:
        if case_dir:
            out = case_dir / "work" / "exemplar_feedback_draft.md"
        else:
            out = repo_root() / "math-modeling-review-cases" / "_learning" / "exemplar_feedback_draft.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(feedback_template(), encoding="utf-8")
    print(f"template={out}")


def parse_feedback_draft(text: str) -> list[dict[str, Any]]:
    blocks = re.split(r"(?m)^---\s*$", text)
    records: list[dict[str, Any]] = []
    for block in blocks:
        item = parse_issue_block(block)
        if not any(item.get(key) for key in ("title", "source_url", "source_path", "positive_signals", "negative_signals")):
            continue
        for key in ("applicable_tags", "useful_for"):
            if isinstance(item.get(key), str):
                item[key] = split_terms(item[key])
        item["recorded_at"] = _dt.datetime.now().isoformat(timespec="seconds")
        records.append(item)
    return records


def validate_feedback(records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, item in enumerate(records, 1):
        if not item.get("title"):
            errors.append(f"{index:02d}: missing title")
        if not item.get("source_url") and not item.get("source_path"):
            errors.append(f"{index:02d}: missing source_url or source_path")
        if not item.get("authority_level"):
            errors.append(f"{index:02d}: missing authority_level")
        if not item.get("positive_signals") and not item.get("negative_signals") and not item.get("scoring_implications"):
            errors.append(f"{index:02d}: missing feedback signals")
    return errors


def build_feedback(args: argparse.Namespace) -> None:
    draft = Path(args.draft).resolve()
    records = parse_feedback_draft(draft.read_text(encoding="utf-8"))
    errors = validate_feedback(records)
    if errors:
        raise SystemExit("Invalid feedback draft:\n" + "\n".join(errors))

    case_dir = Path(args.case_dir).resolve() if args.case_dir else None
    if args.out:
        out = Path(args.out).resolve()
    elif case_dir:
        out = case_dir / "work" / "exemplar_feedback.json"
    else:
        out = draft.with_suffix(".json")
    write_json(out, records)

    appended = ""
    if not args.no_append_log:
        log_path = Path(args.log).resolve() if args.log else repo_root() / "math-modeling-review-cases" / "_learning" / "exemplar_feedback_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            for item in records:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        appended = str(log_path)

    result = {"records": len(records), "json": str(out), "appended_log": appended}
    print(json.dumps(result, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reusable tools for the 13-cumcm-paper-review skill.")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init-case", help="Create a case folder and copy problem/paper files.")
    init.add_argument("--case-dir", required=True)
    init.add_argument("--problem", action="append")
    init.add_argument("--paper", action="append")
    init.set_defaults(func=copy_inputs)

    extract = sub.add_parser("extract", help="Extract readable text/profile files from a case folder.")
    extract.add_argument("--case-dir", required=True)
    extract.set_defaults(func=extract_case)

    render = sub.add_parser("render-pdf", help="Render a PDF and build a figure/table inventory.")
    render.add_argument("--case-dir", required=True)
    render.add_argument("--pdf")
    render.add_argument("--scale", type=float, default=2.0)
    render.add_argument("--cols", type=int, default=5)
    render.add_argument("--thumb-width", type=int, default=300)
    render.set_defaults(func=render_case_pdf)

    media = sub.add_parser("inspect-docx-media", help="Extract DOCX media and build a contact sheet.")
    media.add_argument("--case-dir", required=True)
    media.add_argument("--docx")
    media.add_argument("--limit", type=int, default=24)
    media.set_defaults(func=inspect_docx_media)

    inventory = sub.add_parser("build-figure-inventory", help="Build structured figure/table inventory JSON and Markdown for a PDF or DOCX case.")
    inventory.add_argument("--case-dir", required=True)
    inventory.add_argument("--file")
    inventory.add_argument("--format", choices=("auto", "pdf", "docx"), default="auto")
    inventory.add_argument("--out", help="Output JSON path. Defaults to work/figure_inventory.json.")
    inventory.add_argument("--md-out", help="Output Markdown path. Defaults to work/figure_inventory.md.")
    inventory.set_defaults(func=build_figure_inventory)

    patterns = sub.add_parser("build-figure-patterns", help="Learn figure/table type patterns from text-rich exemplar papers.")
    patterns.add_argument("--manifest", default="math-modeling-intake/_catalog/manifest.json")
    patterns.add_argument("--out")
    patterns.add_argument("--md-out")
    patterns.add_argument("--max-samples", type=int, default=0)
    patterns.add_argument("--max-pages", type=int, default=0)
    patterns.add_argument("--examples-per-type", type=int, default=12)
    patterns.set_defaults(func=build_figure_patterns)

    search_refs = sub.add_parser("search-references", help="Search authoritative external references and write reference cards/report.")
    search_refs.add_argument("--case-dir")
    search_refs.add_argument("--labels", help="Comma-separated paper labels, e.g. 优化,时间序列,图表密集")
    search_refs.add_argument("--methods", help="Comma-separated model/method keywords, e.g. 灰色预测,线性规划")
    search_refs.add_argument("--topic", help="Problem topic or application domain.")
    search_refs.add_argument("--problem-summary", help="Short problem summary used to generate richer queries.")
    search_refs.add_argument("--num-results", type=int, default=5)
    search_refs.add_argument("--max-candidates", type=int, default=20)
    search_refs.add_argument("--out")
    search_refs.add_argument("--report")
    search_refs.add_argument("--cards-dir")
    search_refs.add_argument("--mcporter", help="Path to mcporter executable if it is not on PATH.")
    search_refs.add_argument("--dry-run", action="store_true", help="Generate queries and empty report without calling the network.")
    search_refs.add_argument("--no-cards", action="store_true", help="Do not write external reference card drafts.")
    search_refs.set_defaults(func=search_references)

    match = sub.add_parser("match-exemplars", help="Score local exemplar index and write candidate/core exemplar reports.")
    match.add_argument("--case-dir")
    match.add_argument("--index", help="Path to references/exemplars/index.md. Defaults to the skill-bundled index.")
    match.add_argument("--labels", help="Comma-separated paper/problem labels, e.g. 优化,图表密集,多问题结构")
    match.add_argument("--methods", help="Comma-separated model/method labels, e.g. 线性规划,敏感性分析")
    match.add_argument("--data-tags", help="Comma-separated data labels, e.g. 时间序列,大规模数据")
    match.add_argument("--figure-tags", help="Comma-separated figure/table labels, e.g. 流程图,趋势图")
    match.add_argument("--writing-tags", help="Comma-separated writing/structure labels, e.g. 摘要定量清晰,检验完整")
    match.add_argument("--risk-tags", help="Comma-separated risk labels to penalize if matched.")
    match.add_argument("--keywords", help="Comma-separated domain keywords from the paper/problem.")
    match.add_argument("--topic", help="Problem topic or application domain.")
    match.add_argument("--candidates", type=int, default=8, help="Number of candidate exemplars to keep. Recommended 5-8.")
    match.add_argument("--core", type=int, default=5, help="Number of core exemplars to read. Recommended 3-5.")
    match.add_argument("--feedback-log", help="Path to exemplar_feedback_log.jsonl.")
    match.add_argument("--no-feedback", action="store_true", help="Disable historical authoritative feedback hints.")
    match.add_argument("--out")
    match.add_argument("--report")
    match.set_defaults(func=match_exemplars)

    ref_report = sub.add_parser("build-reference-report", help="Build reference_report.md from exemplar matches, external references, and confirmation items.")
    ref_report.add_argument("--case-dir", required=True)
    ref_report.add_argument("--exemplar-match", help="Path to exemplar_match.json. Defaults to work/exemplar_match.json.")
    ref_report.add_argument("--external-refs", help="Path to external_references.json. Defaults to work/external_references.json.")
    ref_report.add_argument("--issues", help="Path to issues JSON. Defaults to work/issues.json and work/figure_issues.json if present.")
    ref_report.add_argument("--figure-review", help="Path to figure_review.json. Defaults to work/figure_review.json.")
    ref_report.add_argument("--out", help="Output Markdown report. Defaults to work/reference_report.md.")
    ref_report.add_argument("--json-out", help="Output structured JSON. Defaults to work/reference_report.json.")
    ref_report.set_defaults(func=build_reference_report)

    regression = sub.add_parser("run-regression-tests", help="Run local fixture regression tests for DOCX/PDF/figure JSON/reference report.")
    regression.add_argument("--run-dir", help="Directory for generated regression fixtures and outputs. Defaults to ignored math-modeling-review-cases/_regression/<timestamp>.")
    regression.add_argument("--fail-fast", action="store_true", help="Stop on the first failing regression test.")
    regression.set_defaults(func=run_regression_tests)

    feedback_template_parser = sub.add_parser("make-feedback-template", help="Create a draft template for authoritative commentary feedback.")
    feedback_template_parser.add_argument("--case-dir")
    feedback_template_parser.add_argument("--out")
    feedback_template_parser.set_defaults(func=make_feedback_template)

    feedback_build = sub.add_parser("build-feedback", help="Convert authoritative commentary feedback draft to JSON/JSONL learning records.")
    feedback_build.add_argument("--draft", required=True)
    feedback_build.add_argument("--case-dir")
    feedback_build.add_argument("--out")
    feedback_build.add_argument("--log", help="JSONL learning log path. Defaults to math-modeling-review-cases/_learning/exemplar_feedback_log.jsonl.")
    feedback_build.add_argument("--no-append-log", action="store_true")
    feedback_build.set_defaults(func=build_feedback)

    template = sub.add_parser("make-issues-template", help="Create a Markdown draft template for review issues.")
    template.add_argument("--format", choices=("docx", "pdf"), required=True)
    template.add_argument("--case-dir")
    template.add_argument("--out")
    template.set_defaults(func=make_issues_template)

    build = sub.add_parser("build-issues", help="Convert a Markdown issues draft into validated issues JSON.")
    build.add_argument("--format", choices=("docx", "pdf"), required=True)
    build.add_argument("--draft", required=True)
    build.add_argument("--case-dir")
    build.add_argument("--out")
    build.set_defaults(func=build_issues)

    figure_template = sub.add_parser("make-figure-review-template", help="Create a structured figure/table review draft template.")
    figure_template.add_argument("--format", choices=("docx", "pdf"), required=True)
    figure_template.add_argument("--case-dir")
    figure_template.add_argument("--out")
    figure_template.set_defaults(func=make_figure_review_template)

    figure_issues = sub.add_parser("build-figure-issues", help="Convert structured figure/table review records into issues JSON.")
    figure_issues.add_argument("--format", choices=("docx", "pdf"), required=True)
    figure_issues.add_argument("--draft", required=True)
    figure_issues.add_argument("--case-dir")
    figure_issues.add_argument("--out")
    figure_issues.add_argument("--records-out")
    figure_issues.set_defaults(func=build_figure_issues)

    docx_review = sub.add_parser("write-docx-review", help="Apply visible DOCX highlights and prompt paragraphs from issues JSON.")
    docx_review.add_argument("--case-dir", required=True)
    docx_review.add_argument("--issues", required=True)
    docx_review.add_argument("--src")
    docx_review.add_argument("--out")
    docx_review.add_argument("--labels")
    docx_review.add_argument("--references")
    docx_review.set_defaults(func=write_docx_review)

    pdf_review = sub.add_parser("write-pdf-review", help="Apply visible PDF outline markers and appended prompt pages from issues JSON.")
    pdf_review.add_argument("--case-dir", required=True)
    pdf_review.add_argument("--issues", required=True)
    pdf_review.add_argument("--src")
    pdf_review.add_argument("--out")
    pdf_review.add_argument("--labels")
    pdf_review.add_argument("--references")
    pdf_review.set_defaults(func=write_pdf_review)

    verify = sub.add_parser("verify-pdf", help="Check reviewed PDF page/locator counts and render key pages.")
    verify.add_argument("--case-dir", required=True)
    verify.add_argument("--pdf", required=True)
    verify.add_argument("--original")
    verify.add_argument("--applied")
    verify.add_argument("--max-pages", type=int, default=24)
    verify.add_argument("--cols", type=int, default=4)
    verify.add_argument("--thumb-width", type=int, default=360)
    verify.add_argument("--min-marker-pixels", type=int, default=30)
    verify.add_argument("--min-non-white-ratio", type=float, default=0.001)
    verify.set_defaults(func=verify_pdf_review)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
