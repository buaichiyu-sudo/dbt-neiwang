import re

_REF_PATTERN = re.compile(r"\{\{\s*ref\((?P<args>.*?)\)\s*\}\}", re.IGNORECASE | re.DOTALL)
_SOURCE_PATTERN = re.compile(r"\{\{\s*source\((?P<args>.*?)\)\s*\}\}", re.IGNORECASE | re.DOTALL)
_VAR_PATTERN = re.compile(r"\{\{\s*var\((?P<args>.*?)\)\s*\}\}", re.IGNORECASE | re.DOTALL)
_CONFIG_PATTERN = re.compile(r"\{\{\s*config\((?P<args>.*?)\)\s*\}\}", re.IGNORECASE | re.DOTALL)
_JINJA_BLOCK_PATTERN = re.compile(r"\{%.*?%\}", re.DOTALL)
_ANY_EXPR_PATTERN = re.compile(r"\{\{.*?\}\}", re.DOTALL)


def _split_macro_args(arg_str: str) -> list[str]:
    parts = [part.strip() for part in arg_str.split(",") if part.strip()]
    return [part.strip("\"'") for part in parts]


def render_dbt_sql_for_validation(sql: str) -> str:
    """Best-effort dbt/Jinja macro rendering for parser/EXPLAIN validation paths.

    This does not run a real dbt compilation step. It replaces common dbt macros with
    SQL-safe stand-ins so downstream sqlglot and EXPLAIN checks can run.
    """

    rendered = sql

    def replace_ref(match: re.Match[str]) -> str:
        args = _split_macro_args(match.group("args"))
        return args[-1] if args else "unknown_ref"

    def replace_source(match: re.Match[str]) -> str:
        args = _split_macro_args(match.group("args"))
        if len(args) >= 2:
            return f"{args[0]}.{args[1]}"
        return "unknown_source"

    def replace_var(match: re.Match[str]) -> str:
        args = _split_macro_args(match.group("args"))
        return args[0] if args else "unknown_var"

    rendered = _CONFIG_PATTERN.sub("", rendered)
    rendered = _REF_PATTERN.sub(replace_ref, rendered)
    rendered = _SOURCE_PATTERN.sub(replace_source, rendered)
    rendered = _VAR_PATTERN.sub(replace_var, rendered)
    rendered = _JINJA_BLOCK_PATTERN.sub("", rendered)
    rendered = _ANY_EXPR_PATTERN.sub("jinja_expr", rendered)

    return rendered
