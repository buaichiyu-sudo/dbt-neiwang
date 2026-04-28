import re

_REF_PATTERN = re.compile(r"\{\{\s*ref\s*\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}", re.IGNORECASE)
_SOURCE_PATTERN = re.compile(
    r"\{\{\s*source\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}",
    re.IGNORECASE,
)
_VAR_PATTERN = re.compile(
    r"\{\{\s*var\s*\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*([^)]+))?\)\s*\}\}",
    re.IGNORECASE,
)


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
        return value[1:-1]
    return value


def render_dbt_sql(sql: str) -> str:
    """Render common dbt macros into executable SQL for parser/EXPLAIN checks.

    This is a lightweight preprocessor intended for runtime validation only.
    """

    def replace_ref(match: re.Match[str]) -> str:
        model_name = match.group(1)
        return model_name

    def replace_source(match: re.Match[str]) -> str:
        source_name = match.group(1)
        table_name = match.group(2)
        if source_name:
            return f"{source_name}.{table_name}"
        return table_name

    def replace_var(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default_expr = match.group(2)
        if default_expr:
            return _strip_quotes(default_expr)
        return f"__var_{var_name}"

    rendered = _REF_PATTERN.sub(replace_ref, sql)
    rendered = _SOURCE_PATTERN.sub(replace_source, rendered)
    rendered = _VAR_PATTERN.sub(replace_var, rendered)
    return rendered
