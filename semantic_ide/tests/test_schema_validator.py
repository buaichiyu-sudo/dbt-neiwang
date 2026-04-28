from pathlib import Path
from core.pipeline.schema_validator import validate_semantic_yaml


def test_schema_validator_pass():
    yml = """
version: 2
models:
  - name: ads_demo
    description: demo
    metrics:
      - name: m1
        description: d1
        type: ratio
"""
    res = validate_semantic_yaml(yml, Path("assets/schemas/semantic_output.schema.json"))
    assert res.ok


def test_schema_validator_fail():
    yml = "version: 2\nmodels: []"
    res = validate_semantic_yaml(yml, Path("assets/schemas/semantic_output.schema.json"))
    assert not res.ok
