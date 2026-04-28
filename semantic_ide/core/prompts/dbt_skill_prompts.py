"""Prompt loading for Semantic-IDE.

Supports two modes:
1) direct: load prompt text directly from a local dbt-agent-skills checkout/installation
2) distilled: fallback to built-in condensed prompts
"""

from __future__ import annotations

import json
import os
from pathlib import Path


DISTILLED_SYSTEM_PROMPT_STRICT = """
你是资深 dbt 工程师。严格遵守：
1) 只基于输入骨架补充 description 与 metrics，不可新增未知字段。
2) SQL 必须使用 ref()/source()，禁止硬编码跨层表名。
3) 输出仅允许两个代码块：```yaml 与 ```sql。
4) SQL WHERE 必须包含 dt 分区过滤。
5) 若不确定字段语义，写明 assumptions，不可编造。
""".strip()

DISTILLED_SYSTEM_PROMPT_REPAIR = """
你将修复上一次输出的结构错误。
必须根据给定 json schema 报错逐项修复。
仍然只输出 ```yaml 与 ```sql 两个代码块。
""".strip()


def load_prompt_version() -> dict:
    version_path = Path(__file__).with_name("version.json")
    return json.loads(version_path.read_text(encoding="utf-8"))


def _read_skills_files(base_dir: Path, relative_files: list[str]) -> str:
    chunks: list[str] = []
    for rel in relative_files:
        p = base_dir / rel
        if not p.exists():
            raise FileNotFoundError(f"skills 文件不存在: {p}")
        chunks.append(f"\n# From: {rel}\n{p.read_text(encoding='utf-8')}")
    return "\n".join(chunks)


def load_system_prompt(mode: str = "direct", repair: bool = False) -> str:
    """Load prompt bundle.

    direct mode requires env variables:
    - DBT_AGENT_SKILLS_PATH: local checkout/install path
    - DBT_AGENT_SKILLS_FILES: comma-separated relative file paths

    Example:
    DBT_AGENT_SKILLS_PATH=/data/dbt-agent-skills
    DBT_AGENT_SKILLS_FILES=README.md,examples/metricflow_prompt.md
    """
    mode = (mode or "direct").lower()

    if mode == "direct":
        base = os.getenv("DBT_AGENT_SKILLS_PATH", "").strip()
        files_raw = os.getenv("DBT_AGENT_SKILLS_FILES", "README.md")
        rel_files = [x.strip() for x in files_raw.split(",") if x.strip()]
        if not base:
            raise RuntimeError("direct 模式需要 DBT_AGENT_SKILLS_PATH")
        direct_text = _read_skills_files(Path(base), rel_files)
        repair_clause = "\n你当前处于修复模式：仅修复结构错误，仍然只输出 YAML/SQL 代码块。" if repair else ""
        return (
            "你必须严格遵循以下 dbt-agent-skills 原始内容，不得偏离。\n"
            f"{direct_text}\n"
            "额外硬规则：SQL 必须含 dt 分区过滤；输出仅包含 ```yaml 和 ```sql 两个代码块。"
            f"{repair_clause}"
        )

    if mode == "distilled":
        return DISTILLED_SYSTEM_PROMPT_REPAIR if repair else DISTILLED_SYSTEM_PROMPT_STRICT

    raise ValueError(f"未知 prompt 模式: {mode}")
