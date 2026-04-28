from pathlib import Path

from core.config import Settings
from core.llm.parser import extract_yaml_sql_blocks
from core.llm.qwen_client import QwenClient
from core.models import GenerationResult, Intent, ValidationResult
from core.pipeline.schema_validator import validate_semantic_yaml
from core.prompts.dbt_skill_prompts import load_system_prompt


class SemanticGenerator:
    def __init__(self, llm: QwenClient, schema_path: Path, settings: Settings):
        self.llm = llm
        self.schema_path = schema_path
        self.settings = settings

    def generate(self, intent: Intent, table_name: str, skeleton_yaml: str) -> tuple[GenerationResult | None, ValidationResult]:
        user_prompt = (
            f"表名: {table_name}\n"
            f"意图: {intent.model_dump_json(ensure_ascii=False)}\n"
            f"骨架:\n{skeleton_yaml}\n"
            "请输出最终 yaml 与 sql。"
        )

        system_prompt = load_system_prompt(mode=self.settings.dbt_agent_skills_mode, repair=False)
        last_yaml = ""
        for _ in range(3):
            reply = self.llm.chat(system_prompt, user_prompt)
            yml, sql = extract_yaml_sql_blocks(reply)
            last_yaml = yml
            result = validate_semantic_yaml(yml, self.schema_path)
            if result.ok:
                return GenerationResult(sql=sql, yml=yml), result
            user_prompt = f"上次输出不合法，请修复。错误: {result.message}\n原始输出:\n{reply}"
            system_prompt = load_system_prompt(mode=self.settings.dbt_agent_skills_mode, repair=True)

        return None, validate_semantic_yaml(last_yaml, self.schema_path)
