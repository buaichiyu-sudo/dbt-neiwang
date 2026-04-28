from sqlglot import parse_one, exp

from core.errors import E_AST_NO_DT
from core.models import ValidationResult


def _where_contains_required(where_node: exp.Where | None, required_cols: list[str]) -> bool:
    if where_node is None:
        return False
    where_sql = where_node.sql().lower()
    return any(col.lower() in where_sql for col in required_cols)


def enforce_partition_filter(sql: str, required_cols: list[str] | None = None) -> ValidationResult:
    """Validate partition filter in top query and subqueries.

    Rule:
    - every SELECT node that has a FROM clause must include WHERE with required partition columns.
    """
    required_cols = required_cols or ["dt"]
    try:
        ast = parse_one(sql)
    except Exception as exc:
        return ValidationResult(ok=False, error_code=E_AST_NO_DT, message=f"SQL 解析失败: {exc}")

    for select_node in ast.find_all(exp.Select):
        has_from = select_node.args.get("from") is not None
        if not has_from:
            continue
        where_node = select_node.args.get("where")
        if not _where_contains_required(where_node, required_cols):
            return ValidationResult(
                ok=False,
                error_code=E_AST_NO_DT,
                message=f"检测到查询块缺少分区过滤（需要 {required_cols}）",
            )

    return ValidationResult(ok=True, message="AST 分区校验通过")
