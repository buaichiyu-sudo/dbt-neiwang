import json
from pathlib import Path
import yaml
from jsonschema import validate, ValidationError

from core.errors import E_SCHEMA_INVALID
from core.models import ValidationResult


def validate_semantic_yaml(yaml_text: str, schema_path: Path) -> ValidationResult:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        payload = yaml.safe_load(yaml_text)
        validate(instance=payload, schema=schema)
        return ValidationResult(ok=True, message="schema 校验通过")
    except (ValidationError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return ValidationResult(ok=False, error_code=E_SCHEMA_INVALID, message=str(exc))
