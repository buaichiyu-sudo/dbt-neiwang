import json
import re


def parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def extract_yaml_sql_blocks(text: str) -> tuple[str, str]:
    yaml_match = re.search(r"```yaml\n(.*?)```", text, flags=re.S)
    sql_match = re.search(r"```sql\n(.*?)```", text, flags=re.S)
    if not yaml_match or not sql_match:
        raise ValueError("模型输出缺少 yaml/sql 代码块")
    return yaml_match.group(1).strip(), sql_match.group(1).strip()
