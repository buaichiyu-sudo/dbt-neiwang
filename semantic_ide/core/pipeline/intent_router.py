import json
from pathlib import Path

from jsonschema import validate, ValidationError

from core.llm.qwen_client import QwenClient
from core.llm.parser import parse_json
from core.models import Intent
from core.prompts.intent_prompts import INTENT_SYSTEM_PROMPT


class IntentRouter:
    def __init__(self, llm: QwenClient, schema_path: Path):
        self.llm = llm
        self.schema_path = schema_path

    def route(self, raw_input: str) -> Intent:
        reply = self.llm.chat(INTENT_SYSTEM_PROMPT, f"请输出业务意图JSON：\n{raw_input}")
        data = parse_json(reply)
        self._validate_schema(data)
        return Intent(**data)

    def _validate_schema(self, payload: dict) -> None:
        schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        try:
            validate(instance=payload, schema=schema)
        except ValidationError as exc:
            raise ValueError(f"Intent JSON 不符合 schema: {exc.message}") from exc

    @staticmethod
    def should_block(intent: Intent) -> bool:
        return intent.complexity == "High" or intent.recommended_layer == "DWD"
