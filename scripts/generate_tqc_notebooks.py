#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import textwrap
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "doc"
OUT_DIR = ROOT / "Questions"

PROBLEM_HEADER_RE = re.compile(r"^(#{1,2})\s+(\d{3})\s+(.+?)\s*$", re.MULTILINE)
TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)

EXAMPLE_INPUT_RE = re.compile(r"^\s*(?:#+\s*)?範例輸入(?:\s*\d+)?\s*[:：]?\s*$")
EXAMPLE_OUTPUT_RE = re.compile(r"^\s*(?:#+\s*)?範例輸出(?:\s*\d+)?\s*[:：]?\s*$")
INLINE_INPUT_RE = re.compile(r"^\s*(?:[-*]\s*)?輸入[:：]\s*(.*?)\s*$")
INLINE_OUTPUT_RE = re.compile(r"^\s*(?:[-*]\s*)?輸出[:：]\s*(.*?)\s*$")


def notebook_name(doc_path: Path) -> str:
    stem = doc_path.stem
    prefix = "TQC_Python_"
    if stem.startswith(prefix):
        stem = stem[len(prefix) :]
    return f"{stem}.ipynb"


def clean_block(text: str) -> str:
    text = text.replace("\r\n", "\n").strip("\n")
    lines = text.splitlines()
    return "\n".join(line.rstrip() for line in lines)


def is_terminator(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped == "---":
        return True
    if PROBLEM_HEADER_RE.match(line):
        return True
    if EXAMPLE_INPUT_RE.match(line) or EXAMPLE_OUTPUT_RE.match(line):
        return True
    if INLINE_INPUT_RE.match(line) or INLINE_OUTPUT_RE.match(line):
        return True
    return False


def consume_block(lines: list[str], start: int, inline_text: str = "") -> tuple[str, int]:
    content: list[str] = []
    inline_text = inline_text.strip()
    index = start + 1

    if inline_text:
        content.append(inline_text)

    while index < len(lines) and not lines[index].strip():
        index += 1

    if index < len(lines) and lines[index].lstrip().startswith("```"):
        index += 1
        while index < len(lines) and not lines[index].lstrip().startswith("```"):
            content.append(lines[index].rstrip("\n"))
            index += 1
        if index < len(lines):
            index += 1
        return clean_block("\n".join(content)), index

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped and content:
            break
        if is_terminator(line):
            break
        if stripped:
            content.append(line.strip() if line.startswith("  ") else line.rstrip())
        index += 1

    return clean_block("\n".join(content)), index


def is_real_example_output(output_text: str) -> bool:
    if not output_text:
        return False
    invalid_markers = ["(略)", "（略）", "輸出為", "依題目要求", "欄位寬度"]
    return not any(marker in output_text for marker in invalid_markers)


def extract_examples(section_text: str) -> list[dict[str, str]]:
    lines = section_text.splitlines()
    cases: list[dict[str, str]] = []
    pending_input: str | None = None
    seen: set[tuple[str, str]] = set()
    index = 0

    while index < len(lines):
        line = lines[index]

        if EXAMPLE_INPUT_RE.match(line):
            pending_input, index = consume_block(lines, index)
            continue

        if EXAMPLE_OUTPUT_RE.match(line):
            output_text, index = consume_block(lines, index)
            if pending_input and is_real_example_output(output_text):
                key = (pending_input, output_text)
                if key not in seen:
                    seen.add(key)
                    cases.append({"input": pending_input, "expected": output_text})
            pending_input = None
            continue

        input_match = INLINE_INPUT_RE.match(line)
        if input_match:
            pending_input, index = consume_block(lines, index, input_match.group(1))
            continue

        output_match = INLINE_OUTPUT_RE.match(line)
        if output_match:
            output_text, index = consume_block(lines, index, output_match.group(1))
            if pending_input and is_real_example_output(output_text):
                key = (pending_input, output_text)
                if key not in seen:
                    seen.add(key)
                    cases.append({"input": pending_input, "expected": output_text})
            pending_input = None
            continue

        index += 1

    return cases


def parse_problems(text: str) -> list[dict[str, object]]:
    matches = list(PROBLEM_HEADER_RE.finditer(text))
    problems: list[dict[str, object]] = []
    for pos, match in enumerate(matches):
        start = match.start()
        end = matches[pos + 1].start() if pos + 1 < len(matches) else len(text)
        section = text[start:end].strip()
        problems.append(
            {
                "code": match.group(2),
                "title": match.group(3).strip(),
                "section_markdown": section,
                "examples": extract_examples(section),
            }
        )
    return problems


def make_markdown_cell(source: str) -> dict[str, object]:
    return {
        "cell_type": "markdown",
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def make_code_cell(source: str) -> dict[str, object]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def render_case_list(examples: list[dict[str, str]]) -> str:
    if not examples:
        return "[]"

    rendered = []
    for case in examples:
        rendered.append(
            "{\n"
            f"    'input': {case['input']!r},\n"
            f"    'expected': {case['expected']!r},\n"
            "}"
        )
    return "[\n" + ",\n".join(rendered) + "\n]"


def build_notebook(doc_path: Path) -> dict[str, object]:
    text = doc_path.read_text(encoding="utf-8")
    title_match = TITLE_RE.search(text)
    title = title_match.group(1).strip() if title_match else doc_path.stem
    problems = parse_problems(text)

    cells: list[dict[str, object]] = []
    header = textwrap.dedent(
        f"""\
        # {title}

        來源：[doc/{doc_path.name}](../doc/{doc_path.name})

        使用方式：
        - 每題請實作 `solve_題號(input_data: str) -> str`
        - 完成後直接執行該題下方的測試 cell
        - 測試比對會保留空白與換行差異，只忽略最後多出的空白行
        """
    )
    cells.append(make_markdown_cell(header))

    helper_code = textwrap.dedent(
        """\
        def normalize_output(text):
            if not isinstance(text, str):
                text = str(text)
            text = text.replace("\\r\\n", "\\n")
            return text.rstrip("\\n")


        def run_example_tests(problem_code, func, cases):
            if not cases:
                print(f"{problem_code}: 找不到可自動解析的完整範例，請自行補測試。")
                return

            for idx, case in enumerate(cases, start=1):
                actual = normalize_output(func(case["input"]))
                expected = normalize_output(case["expected"])
                if actual != expected:
                    raise AssertionError(
                        f"[{problem_code} case {idx}]\\n"
                        f"input:\\n{case['input']!r}\\n\\n"
                        f"expected:\\n{expected!r}\\n\\n"
                        f"actual:\\n{actual!r}"
                    )

            print(f"{problem_code}: {len(cases)} 個範例測試通過。")
        """
    )
    cells.append(make_code_cell(helper_code))

    for problem in problems:
        code = problem["code"]
        title_text = problem["title"]
        section_markdown = problem["section_markdown"]
        examples = problem["examples"]

        cells.append(make_markdown_cell(section_markdown))

        solution_stub = textwrap.dedent(
            f"""\
            def solve_{code}(input_data: str) -> str:
                \"\"\"讀入整份標準輸入字串，回傳整份標準輸出字串。\"\"\"
                raise NotImplementedError("Implement solve_{code}")
            """
        )
        cells.append(make_code_cell(solution_stub))

        tests = (
            f"cases_{code} = {render_case_list(examples)}\n"
            f'run_example_tests("{code}", solve_{code}, cases_{code})\n'
        )
        cells.append(make_code_cell(tests))

        custom_test = (
            "# 自訂測試區\n"
            '# custom_input = """"""\n'
            f"# print(solve_{code}(custom_input))\n"
        )
        cells.append(make_code_cell(custom_test))

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3",
            },
            "source_md": str(doc_path.relative_to(ROOT)),
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for doc_path in sorted(DOC_DIR.glob("TQC_Python_*.md")):
        notebook = build_notebook(doc_path)
        output_path = OUT_DIR / notebook_name(doc_path)
        output_path.write_text(
            json.dumps(notebook, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(output_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
