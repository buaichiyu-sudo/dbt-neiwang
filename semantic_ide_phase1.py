#!/usr/bin/env python3
"""Semantic-IDE Phase 1 single-file MVP.

Run:
    streamlit run semantic_ide_phase1.py

This script is intentionally self-contained so it can be dropped into a dbt
project root and run directly in intranet environments.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st
import yaml
from jsonschema import ValidationError, validate
from sqlglot import exp, parse_one


# =========================
# Config & constants
# =========================

INTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["intent_type", "metrics", "dimensions", "filters", "complexity"],
    "properties": {
        "intent_type": {"type": "string"},
        "metrics": {"type": "array", "items": {"type": "string"}},
        "dimensions": {"type": "array", "items": {"type": "string"}},
        "filters": {"type": "object"},
        "complexity": {"type": "string", "enum": ["Low", "Medium", "High"]},
        "reason": {"type": "string"},
    },
}

SEMANTIC_YAML_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["version", "models"],
    "properties": {
        "version": {"type": "integer"},
        "models": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["name", "description", "metrics"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "description", "type"],
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "type": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    },
}

DBT_AGENT_SKILLS_STYLE_SYSTEM_PROMPT = """
You are a strict dbt semantic modeling assistant.
Rules:
1) Only enrich metric definitions and descriptions based on provided dbt codegen skeleton.
2) Do not fabricate fields/tables not present in provided context.
3) SQL must use ref()/source(), never hardcode production table names.
4) SQL WHERE must include partition filter on dt.
5) Output EXACTLY two fenced code blocks: one ```yaml and one ```sql.
6) If uncertain, state assumptions in description fields; never hallucinate facts.
""".strip()

INTENT_SYSTEM_PROMPT = """
Convert user business text into Business Intent JSON.
Return ONLY JSON with keys:
intent_type, metrics, dimensions, filters, complexity, reason.
If request is complex temporal/event-chain/log-correlation, set complexity=High.
""".strip()


@dataclass
class AppConfig:
    qwen_api_base: str = os.getenv("QWEN_API_BASE", "")
    qwen_api_key: str = os.getenv("QWEN_API_KEY", "")
    qwen_model: str = os.getenv("QWEN_MODEL", "qwen3.5")
    dbt_project_dir: str = os.getenv("DBT_PROJECT_DIR", ".")
    dbt_profiles_dir: str = os.getenv("DBT_PROFILES_DIR", os.path.expanduser("~/.dbt"))
    doris_host: str = os.getenv("DORIS_HOST", "")
    doris_port: int = int(os.getenv("DORIS_PORT", "9030"))
    doris_user: str = os.getenv("DORIS_USER", "")
    doris_password: str = os.getenv("DORIS_PASSWORD", "")
    doris_database: str = os.getenv("DORIS_DATABASE", "")
    mock_mode: bool = os.getenv("SEMANTIC_IDE_MOCK", "true").lower() == "true"


# =========================
# Utility functions
# =========================


def parse_multimodal_input(nl_text: str, legacy_sql: str, excel_text: str) -> str:
    """Merge different input modalities into one canonical prompt text."""
    blocks = []
    if nl_text.strip():
        blocks.append(f"[Natural Language]\n{nl_text.strip()}")
    if legacy_sql.strip():
        blocks.append(f"[Legacy SQL]\n{legacy_sql.strip()}")
    if excel_text.strip():
        blocks.append(f"[Excel Spec]\n{excel_text.strip()}")
    return "\n\n".join(blocks).strip()


def _chat_qwen(system_prompt: str, user_prompt: str, cfg: AppConfig) -> str:
    """Call Qwen API or return deterministic mock output for offline development."""
    if cfg.mock_mode or not cfg.qwen_api_base:
        if "Business Intent JSON" in user_prompt or "intent_type" in user_prompt:
            return json.dumps(
                {
                    "intent_type": "metric_request",
                    "metrics": ["charging_efficiency"],
                    "dimensions": ["station_id", "date"],
                    "filters": {"date": "yesterday"},
                    "complexity": "Low",
                    "reason": "常规聚合指标，复杂度低",
                },
                ensure_ascii=False,
            )
        return """```yaml
version: 2
models:
  - name: ads_charging_efficiency_daily
    description: 单站昨日充电效率指标
    metrics:
      - name: charging_efficiency
        description: 充电效率=总充电电量/总充电时长
        type: ratio
```
```sql
select
  station_id,
  dt,
  sum(charge_kwh)/nullif(sum(charge_hours), 0) as charging_efficiency
from {{ ref('dws_charge_order_di') }}
where dt = '{{ var("biz_date") }}'
group by station_id, dt
```
"""

    payload = {
        "model": cfg.qwen_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
    }
    resp = requests.post(
        f"{cfg.qwen_api_base.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {cfg.qwen_api_key}"},
        json=payload,
        timeout=90,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _extract_json(text: str) -> dict[str, Any]:
    """Extract strict JSON payload from model output."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def _extract_yaml_sql(text: str) -> tuple[str, str]:
    """Extract YAML and SQL fenced blocks from model output."""
    yaml_match = re.search(r"```yaml\n(.*?)```", text, flags=re.S)
    sql_match = re.search(r"```sql\n(.*?)```", text, flags=re.S)
    if not yaml_match or not sql_match:
        raise ValueError("Qwen 输出缺少 yaml/sql 代码块")
    return yaml_match.group(1).strip(), sql_match.group(1).strip()


# =========================
# Core pipeline functions
# =========================


def parse_intent(multimodal_text: str, cfg: AppConfig) -> dict[str, Any]:
    """Convert user text into standardized Business Intent JSON via Qwen."""
    prompt = f"Business Intent JSON only:\n{multimodal_text}"
    raw = _chat_qwen(INTENT_SYSTEM_PROMPT, prompt, cfg)
    intent = _extract_json(raw)
    validate(instance=intent, schema=INTENT_SCHEMA)
    return intent


def generate_dwd_handoff_markdown(intent: dict[str, Any]) -> str:
    """Generate markdown recommendation when complexity is High."""
    return (
        "# 建议转交 DWD 层开发\n\n"
        f"- complexity: **{intent.get('complexity')}**\n"
        f"- reason: {intent.get('reason', '复杂时序或底层报文关联')}\n\n"
        "## 建议动作\n"
        "1. 在 DWD 层先完成报文关联与时序清洗。\n"
        "2. 再在 DWS/ADS 层沉淀可复用指标模型。\n"
    )


def generate_dbt_skeleton(table_names: list[str], cfg: AppConfig) -> str:
    """Call dbt-codegen generate_model_yaml and return skeleton YAML text.

    Ref pattern from dbt-codegen README:
      dbt run-operation generate_model_yaml --args '{"model_names": ["customers"]}'
    """
    if not table_names:
        raise ValueError("至少输入一个表名")

    args = json.dumps({"model_names": table_names}, ensure_ascii=False)
    cmd = [
        "dbt",
        "run-operation",
        "generate_model_yaml",
        "--args",
        args,
        "--project-dir",
        cfg.dbt_project_dir,
        "--profiles-dir",
        cfg.dbt_profiles_dir,
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as exc:
        # Graceful fallback for offline/local mock testing.
        return (
            f"# dbt-codegen failed: {exc}\n"
            "version: 2\nmodels:\n"
            f"  - name: {table_names[0]}\n"
            "    description: ''\n"
            "    columns: []\n"
        )


def generate_semantic_yaml_sql(
    multimodal_text: str,
    intent: dict[str, Any],
    skeleton_yaml: str,
    cfg: AppConfig,
    max_retries: int = 3,
) -> tuple[str, str]:
    """Generate semantic YAML + SQL with schema validation and auto-retry repair."""
    user_prompt = (
        "You are generating dbt semantic assets.\n"
        f"Intent JSON:\n{json.dumps(intent, ensure_ascii=False)}\n\n"
        f"dbt-codegen skeleton:\n{skeleton_yaml}\n\n"
        f"User input:\n{multimodal_text}\n"
        "Output only YAML + SQL code fences."
    )

    last_error = ""
    for attempt in range(1, max_retries + 1):
        raw = _chat_qwen(DBT_AGENT_SKILLS_STYLE_SYSTEM_PROMPT, user_prompt, cfg)
        yml_text, sql_text = _extract_yaml_sql(raw)
        try:
            validate_semantic_yaml(yml_text)
            return yml_text, sql_text
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            user_prompt = (
                f"Previous output invalid (attempt={attempt}). Fix strictly.\n"
                f"Validation error:\n{last_error}\n\n"
                f"Previous output:\n{raw}\n"
            )

    raise ValueError(f"YAML 校验失败，重试 {max_retries} 次后仍不通过: {last_error}")


def validate_semantic_yaml(yml_text: str) -> None:
    """Validate semantic YAML structure with jsonschema."""
    parsed = yaml.safe_load(yml_text)
    validate(instance=parsed, schema=SEMANTIC_YAML_SCHEMA)


def validate_sql_guardrail(sql: str, required_partition_col: str = "dt") -> None:
    """AST guardrail: enforce WHERE contains dt partition filter."""
    try:
        ast = parse_one(sql)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"SQL 语法解析失败: {exc}") from exc

    where_node = ast.find(exp.Where)
    if not where_node:
        raise ValueError("SQL 缺少 WHERE 条件，禁止执行")

    where_sql = where_node.sql().lower()
    if required_partition_col.lower() not in where_sql:
        raise ValueError(f"SQL WHERE 未包含分区字段 `{required_partition_col}`")


def run_doris_explain(sql: str, cfg: AppConfig) -> str:
    """Optional EXPLAIN check for SQL syntax/join plan.

    In mock mode this returns a simulated result.
    """
    if cfg.mock_mode:
        return "MOCK: EXPLAIN passed"

    # Optional dependency import kept inside function for self-contained script.
    try:
        import pymysql  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("真实 EXPLAIN 需要安装 pymysql") from exc

    conn = pymysql.connect(
        host=cfg.doris_host,
        port=cfg.doris_port,
        user=cfg.doris_user,
        password=cfg.doris_password,
        database=cfg.doris_database,
        read_timeout=30,
        write_timeout=30,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"EXPLAIN {sql}")
            rows = cur.fetchall()
            return f"EXPLAIN rows={len(rows)}"
    finally:
        conn.close()


def preview_limit_10(sql: str) -> pd.DataFrame:
    """Preview function.

    For MVP single-file portability, returns mock dataframe.
    Replace with real Doris query execution when needed.
    """
    _ = sql
    return pd.DataFrame(
        {
            "dt": ["2026-04-27", "2026-04-28"],
            "station_id": ["S001", "S001"],
            "charging_efficiency": [0.84, 0.88],
        }
    )


def write_local_assets(model_name: str, sql: str, yml: str, dbt_project_root: str = ".") -> tuple[Path, Path]:
    """Write generated files into ./models/ under dbt project root."""
    models_dir = Path(dbt_project_root).resolve() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    sql_path = models_dir / f"{model_name}.sql"
    yml_path = models_dir / f"{model_name}.yml"

    sql_path.write_text(sql, encoding="utf-8")
    yml_path.write_text(yml, encoding="utf-8")
    return sql_path, yml_path


# =========================
# Streamlit UI
# =========================


def main() -> None:
    st.set_page_config(page_title="Semantic-IDE Phase1", layout="wide")
    st.title("Semantic-IDE Phase 1 (Single Script MVP)")

    cfg = AppConfig()

    if "intent" not in st.session_state:
        st.session_state.intent = None
    if "yml" not in st.session_state:
        st.session_state.yml = ""
    if "sql" not in st.session_state:
        st.session_state.sql = ""
    if "handoff_md" not in st.session_state:
        st.session_state.handoff_md = ""

    left, right = st.columns(2)

    with left:
        st.subheader("输入区（多模态）")
        model_name = st.text_input("输出模型名", "ads_charging_efficiency_daily")
        table_input = st.text_input("Doris 物理表/模型名（逗号分隔）", "dws_charge_order_di")
        nl_text = st.text_area("自然语言需求", "统计昨日单站充电效率")
        legacy_sql = st.text_area("旧 SQL（可选）", "")
        excel_text = st.text_area("Excel 口径文本（可选）", "")

        if st.button("1) 解析意图"):
            merged = parse_multimodal_input(nl_text, legacy_sql, excel_text)
            try:
                intent = parse_intent(merged, cfg)
                st.session_state.intent = intent
                if intent.get("complexity") == "High":
                    st.session_state.handoff_md = generate_dwd_handoff_markdown(intent)
                else:
                    st.session_state.handoff_md = ""
                st.success("意图解析完成")
            except ValidationError as exc:
                st.error(f"Intent JSON schema 校验失败: {exc}")
            except Exception as exc:  # noqa: BLE001
                st.error(f"意图解析失败: {exc}")

        if st.button("2) 生成语义 YAML + SQL"):
            intent = st.session_state.intent
            if not intent:
                st.warning("请先解析意图")
            elif intent.get("complexity") == "High":
                st.warning("复杂度 High：已阻断 SQL 生成，请查看右侧建议 Markdown")
            else:
                try:
                    merged = parse_multimodal_input(nl_text, legacy_sql, excel_text)
                    tables = [t.strip() for t in table_input.split(",") if t.strip()]
                    skeleton = generate_dbt_skeleton(tables, cfg)
                    yml_text, sql_text = generate_semantic_yaml_sql(merged, intent, skeleton, cfg)
                    validate_sql_guardrail(sql_text, "dt")
                    explain_message = run_doris_explain(sql_text, cfg)

                    st.session_state.yml = yml_text
                    st.session_state.sql = sql_text
                    st.success(f"语义生成成功；{explain_message}")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"语义生成失败: {exc}")

        if st.button("3) 落盘到 ./models/"):
            if not st.session_state.sql or not st.session_state.yml:
                st.warning("请先生成 YAML+SQL")
            else:
                try:
                    sql_path, yml_path = write_local_assets(model_name, st.session_state.sql, st.session_state.yml, cfg.dbt_project_dir)
                    st.success(f"落盘成功:\n{sql_path}\n{yml_path}")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"落盘失败: {exc}")

    with right:
        st.subheader("右侧预览")
        st.markdown("### Business Intent JSON")
        st.json(st.session_state.intent or {})

        if st.session_state.handoff_md:
            st.markdown("### High Complexity 建议")
            st.markdown(st.session_state.handoff_md)

        st.markdown("### YAML 预览")
        st.code(st.session_state.yml, language="yaml")

        st.markdown("### SQL 预览")
        st.code(st.session_state.sql, language="sql")

        st.markdown("### LIMIT 10 数据预览")
        if st.session_state.sql:
            df = preview_limit_10(st.session_state.sql)
            st.dataframe(df, use_container_width=True)
            if {"dt", "charging_efficiency"}.issubset(set(df.columns)):
                st.line_chart(df.set_index("dt")["charging_efficiency"])


if __name__ == "__main__":
    main()
