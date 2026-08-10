#!/usr/bin/env python3
"""Read-only scanner for paired English/Chinese Markdown files and change markers."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
MARKER_RE = re.compile(r"(\+\+\+|/\+\+\+|---|/---)")
MARKER_TYPES = {
    "+++": "addition",
    "---": "deletion",
}
MARKER_CLOSE = {
    "/+++": "+++",
    "/---": "---",
}


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    line: int


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_cn_file(path: Path) -> bool:
    return path.stem.endswith("-CN")


def english_counterpart(cn_path: Path) -> Path:
    stem = cn_path.stem.removesuffix("-CN")
    return cn_path.with_name(f"{stem}{cn_path.suffix}")


def chinese_counterpart(en_path: Path) -> Path:
    return en_path.with_name(f"{en_path.stem}-CN{en_path.suffix}")


def normalize_name(path: Path) -> str:
    stem = path.stem.removesuffix("-CN")
    return re.sub(r"[^a-z0-9]+", "", stem.lower())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_headings(path: Path) -> list[Heading]:
    headings: list[Heading] = []
    in_fence = False
    for lineno, line in enumerate(read_text(path).splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if match:
            headings.append(Heading(len(match.group(1)), match.group(2), lineno))
    return headings


def count_pattern(path: Path, pattern: str) -> int:
    return len(re.findall(pattern, read_text(path), flags=re.MULTILINE))


def structural_hints(en_path: Path, cn_path: Path) -> list[str]:
    hints: list[str] = []
    en_headings = extract_headings(en_path)
    cn_headings = extract_headings(cn_path)

    if len(en_headings) != len(cn_headings):
        hints.append(
            f"heading_count differs: English={len(en_headings)} Chinese={len(cn_headings)}"
        )

    en_levels = [h.level for h in en_headings]
    cn_levels = [h.level for h in cn_headings]
    if en_levels != cn_levels:
        hints.append("heading_level_sequence differs")

    en_fences = count_pattern(en_path, r"^\s*(```|~~~)")
    cn_fences = count_pattern(cn_path, r"^\s*(```|~~~)")
    if en_fences != cn_fences:
        hints.append(f"code_fence_marker_count differs: English={en_fences} Chinese={cn_fences}")

    en_tables = count_pattern(en_path, r"^\s*\|.*\|\s*$")
    cn_tables = count_pattern(cn_path, r"^\s*\|.*\|\s*$")
    if en_tables != cn_tables:
        hints.append(f"table_row_count differs: English={en_tables} Chinese={cn_tables}")

    en_links = count_pattern(en_path, r"\[[^\]]+\]\([^)]+\)")
    cn_links = count_pattern(cn_path, r"\[[^\]]+\]\([^)]+\)")
    if en_links != cn_links:
        hints.append(f"markdown_link_count differs: English={en_links} Chinese={cn_links}")

    en_images = count_pattern(en_path, r"!\[[^\]]*\]\([^)]+\)")
    cn_images = count_pattern(cn_path, r"!\[[^\]]*\]\([^)]+\)")
    if en_images != cn_images:
        hints.append(f"image_count differs: English={en_images} Chinese={cn_images}")

    return hints


def heading_json(path: Path, root: Path) -> dict:
    lines = read_text(path).splitlines()
    headings = extract_headings(path)
    heading_items = []
    for index, heading in enumerate(headings):
        next_line = headings[index + 1].line if index + 1 < len(headings) else len(lines) + 1
        heading_items.append(
            {
                "level": heading.level,
                "text": heading.text,
                "line": heading.line,
                "start_line": heading.line,
                "end_line": next_line - 1,
            }
        )
    return {
        "path": rel(path, root),
        "headings": heading_items,
    }


def line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def preview(text: str, limit: int = 240) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3]}..."


def mask_yaml_frontmatter(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            masked = list(lines)
            masked[0] = "".join("\n" if ch == "\n" else " " for ch in masked[0])
            masked[index] = "".join("\n" if ch == "\n" else " " for ch in masked[index])
            return "".join(masked)
    return text


def section_for_line(headings: list[Heading], line: int) -> dict | None:
    current: Heading | None = None
    for heading in headings:
        if heading.line <= line:
            current = heading
        else:
            break
    if current is None:
        return None
    return {"level": current.level, "text": current.text, "line": current.line}


def extract_markers(path: Path, root: Path) -> dict:
    text = mask_yaml_frontmatter(read_text(path))
    headings = extract_headings(path)
    markers = []
    errors = []
    stack = []

    for match in MARKER_RE.finditer(text):
        token = match.group(1)
        token_line = line_for_offset(text, match.start())
        token_column = match.start() - text.rfind("\n", 0, match.start())

        if token in MARKER_TYPES:
            if stack:
                opener = stack[-1]
                errors.append(
                    {
                        "type": "nested_marker",
                        "path": rel(path, root),
                        "line": token_line,
                        "column": token_column,
                        "message": f"{token} opened before {opener['token']} closed",
                    }
                )
            stack.append({"token": token, "start": match.end(), "line": token_line, "column": token_column})
            continue

        expected_open = MARKER_CLOSE[token]
        if not stack:
            errors.append(
                {
                    "type": "closing_without_opening",
                    "path": rel(path, root),
                    "line": token_line,
                    "column": token_column,
                    "message": f"{token} has no matching opener",
                }
            )
            continue

        opener = stack.pop()
        if opener["token"] != expected_open:
            errors.append(
                {
                    "type": "mismatched_closing_marker",
                    "path": rel(path, root),
                    "line": token_line,
                    "column": token_column,
                    "message": f"{token} closes {expected_open}, but {opener['token']} is open",
                }
            )
            continue

        content = text[opener["start"] : match.start()]
        markers.append(
            {
                "type": MARKER_TYPES[opener["token"]],
                "path": rel(path, root),
                "start_line": opener["line"],
                "end_line": token_line,
                "start_column": opener["column"],
                "end_column": token_column + len(token) - 1,
                "section": section_for_line(headings, opener["line"]),
                "preview": preview(content),
            }
        )

    while stack:
        opener = stack.pop()
        errors.append(
            {
                "type": "unclosed_marker",
                "path": rel(path, root),
                "line": opener["line"],
                "column": opener["column"],
                "message": f"{opener['token']} has no matching closing marker",
            }
        )

    return {"markers": markers, "marker_errors": errors}


def collect_markdown(root: Path, recursive: bool) -> list[Path]:
    pattern = "**/*.md" if recursive else "*.md"
    return sorted(p for p in root.glob(pattern) if p.is_file())


def suggested_pairs(
    unmatched_en: Iterable[Path], unmatched_cn: Iterable[Path], root: Path
) -> list[dict]:
    suggestions: list[dict] = []
    en_list = list(unmatched_en)
    cn_list = list(unmatched_cn)
    for en_path in en_list:
        en_norm = normalize_name(en_path)
        for cn_path in cn_list:
            cn_norm = normalize_name(cn_path)
            if en_norm and en_norm == cn_norm:
                reason = "normalized_basename_match"
            elif en_path.parent == cn_path.parent and (
                en_norm in cn_norm or cn_norm in en_norm
            ):
                reason = "same_folder_partial_basename_match"
            else:
                continue
            suggestions.append(
                {
                    "english": rel(en_path, root),
                    "chinese": rel(cn_path, root),
                    "reason": reason,
                }
            )
    return suggestions


def scan(root: Path, recursive: bool) -> dict:
    markdown_files = collect_markdown(root, recursive)
    en_files = [p for p in markdown_files if not is_cn_file(p)]
    cn_files = [p for p in markdown_files if is_cn_file(p)]
    cn_set = set(cn_files)
    en_set = set(en_files)

    exact_pairs = []
    paired_en = set()
    paired_cn = set()

    for en_path in en_files:
        cn_path = chinese_counterpart(en_path)
        if cn_path in cn_set:
            paired_en.add(en_path)
            paired_cn.add(cn_path)
            en_markers = extract_markers(en_path, root)
            cn_markers = extract_markers(cn_path, root)
            exact_pairs.append(
                {
                    "english": rel(en_path, root),
                    "chinese": rel(cn_path, root),
                    "english_headings": heading_json(en_path, root)["headings"],
                    "chinese_headings": heading_json(cn_path, root)["headings"],
                    "structural_hints": structural_hints(en_path, cn_path),
                    "english_markers": en_markers["markers"],
                    "chinese_markers": cn_markers["markers"],
                    "english_marker_errors": en_markers["marker_errors"],
                    "chinese_marker_errors": cn_markers["marker_errors"],
                }
            )

    missing_chinese = [
        {"english": rel(en_path, root), "expected_chinese": rel(chinese_counterpart(en_path), root)}
        for en_path in en_files
        if en_path not in paired_en
    ]
    missing_english = [
        {"chinese": rel(cn_path, root), "expected_english": rel(english_counterpart(cn_path), root)}
        for cn_path in cn_files
        if cn_path not in paired_cn
    ]

    unmatched_en = [p for p in en_files if p not in paired_en]
    unmatched_cn = [p for p in cn_files if p not in paired_cn]

    return {
        "root": str(root),
        "recursive": recursive,
        "exact_pairs": exact_pairs,
        "missing_chinese": missing_chinese,
        "missing_english": missing_english,
        "suggested_pairs": suggested_pairs(unmatched_en, unmatched_cn, root),
        "unpaired_markers": [
            extract_markers(path, root)
            | {"path": rel(path, root)}
            for path in unmatched_en + unmatched_cn
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan paired English and Chinese Markdown files and change markers without modifying them."
    )
    parser.add_argument("folder", help="Folder containing Markdown files")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search nested folders instead of only the target folder",
    )
    args = parser.parse_args()

    root = Path(args.folder).expanduser().resolve()
    if not root.exists():
        parser.error(f"folder does not exist: {root}")
    if not root.is_dir():
        parser.error(f"not a folder: {root}")

    print(json.dumps(scan(root, args.recursive), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
