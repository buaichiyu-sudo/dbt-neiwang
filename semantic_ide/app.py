from pathlib import Path
import streamlit as st

from core.config import load_settings
from core.llm.qwen_client import QwenClient
from core.models import Intent
from core.pipeline.codegen_adapter import generate_schema_skeleton
from core.pipeline.explain_checker import run_explain
from core.pipeline.guardrails import enforce_partition_filter
from core.pipeline.intent_router import IntentRouter
from core.pipeline.preview_runner import preview_sql_result
from core.pipeline.semantic_generator import SemanticGenerator
from core.pipeline.sink_writer import write_assets
from core.prompts.dbt_skill_prompts import load_prompt_version


st.set_page_config(page_title="Semantic-IDE", layout="wide")
st.title("Semantic-IDE (MVP)")

settings = load_settings()
llm = QwenClient(settings)
router = IntentRouter(llm, Path("assets/schemas/intent.schema.json"))
generator = SemanticGenerator(llm, Path("assets/schemas/semantic_output.schema.json"), settings)
prompt_meta = load_prompt_version()

if "intent" not in st.session_state:
    st.session_state.intent = None
if "gen" not in st.session_state:
    st.session_state.gen = None
if "model_name" not in st.session_state:
    st.session_state.model_name = "ads_charge_efficiency_daily"

left, right = st.columns(2)

with left:
    tables = st.text_input("物理表名（逗号分隔）", "dws_charge_order_di")
    nl_input = st.text_area("自然语言输入", height=120)
    sql_input = st.text_area("旧 SQL（可选）", height=120)
    excel_input = st.text_area("Excel 口径文本（可选）", height=120)

    allow_overwrite = st.checkbox("允许覆盖同名模型文件", value=False)

    merged_input = "\n\n".join(
        x for x in [
            f"[Natural Language]\n{nl_input}" if nl_input.strip() else "",
            f"[Legacy SQL]\n{sql_input}" if sql_input.strip() else "",
            f"[Excel Spec]\n{excel_input}" if excel_input.strip() else "",
        ] if x
    )

    if st.button("解析意图"):
        intent = router.route(merged_input)
        st.session_state.intent = intent

    if st.button("生成语义模型"):
        intent: Intent | None = st.session_state.intent
        if not intent:
            st.error("请先解析意图")
        elif router.should_block(intent):
            st.warning("复杂度高，建议转 DWD 层开发")
            st.markdown(
                f"""
### DWD 开发建议
- complexity: **{intent.complexity}**
- recommended_layer: **{intent.recommended_layer}**
- reasoning: {intent.reasoning_brief}
"""
            )
        else:
            table = tables.split(",")[0].strip()
            try:
                skeleton = generate_schema_skeleton(
                    table,
                    settings.dbt_project_dir,
                    settings.dbt_profiles_dir,
                    settings.mock_mode,
                )
                gen, schema_res = generator.generate(intent, table, skeleton)
                if gen and schema_res.ok:
                    st.session_state.gen = gen
                    st.success("语义生成成功")
                else:
                    st.error(f"生成失败: {schema_res.message}")
            except Exception as exc:
                st.error(f"codegen/生成失败: {exc}")

    if st.button("预览数据"):
        if not st.session_state.gen:
            st.error("请先生成语义模型")
        else:
            try:
                df = preview_sql_result(st.session_state.gen.sql, settings, limit=10)
                st.dataframe(df, use_container_width=True)
                if "dt" in df.columns and "charge_efficiency" in df.columns:
                    st.line_chart(df.set_index("dt")["charge_efficiency"])
            except Exception as exc:
                st.error(f"预览失败: {exc}")

    if st.button("落盘"):
        if not st.session_state.gen:
            st.error("请先生成语义模型")
        else:
            ast_res = enforce_partition_filter(st.session_state.gen.sql)
            if not ast_res.ok:
                st.error(ast_res.message)
            else:
                explain_res = run_explain(st.session_state.gen.sql, settings)
                if not explain_res.ok:
                    st.error(explain_res.message)
                else:
                    ok, msg = write_assets(
                        settings.project_root,
                        st.session_state.model_name,
                        st.session_state.gen.sql,
                        st.session_state.gen.yml,
                        allow_overwrite=allow_overwrite,
                    )
                    st.success(msg) if ok else st.error(msg)

with right:
    st.caption(f"Prompt Bundle: {prompt_meta.get('prompt_bundle_version', 'unknown')} | {prompt_meta.get('source', 'n/a')} | mode={settings.dbt_agent_skills_mode}")
    st.subheader("意图 JSON")
    st.json(st.session_state.intent.model_dump() if st.session_state.intent else {})

    st.subheader("生成 YAML")
    st.code(st.session_state.gen.yml if st.session_state.gen else "", language="yaml")

    st.subheader("生成 SQL")
    st.code(st.session_state.gen.sql if st.session_state.gen else "", language="sql")
