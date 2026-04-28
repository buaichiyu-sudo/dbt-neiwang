from core.config import Settings
from core.errors import E_EXPLAIN_FAIL
from core.models import ValidationResult


def run_explain(sql: str, settings: Settings) -> ValidationResult:
    if settings.mock_mode:
        return ValidationResult(ok=True, message="mock 模式跳过 EXPLAIN")

    try:
        import pymysql  # type: ignore
    except Exception as exc:
        return ValidationResult(ok=False, error_code=E_EXPLAIN_FAIL, message=f"缺少 pymysql 依赖: {exc}")

    if not (settings.doris_host and settings.doris_user and settings.doris_database):
        return ValidationResult(ok=False, error_code=E_EXPLAIN_FAIL, message="缺少 Doris 连接配置")

    try:
        conn = pymysql.connect(
            host=settings.doris_host,
            port=settings.doris_port,
            user=settings.doris_user,
            password=settings.doris_password,
            database=settings.doris_database,
            connect_timeout=10,
            read_timeout=20,
            write_timeout=20,
        )
        with conn.cursor() as cur:
            cur.execute(f"EXPLAIN {sql}")
            rows = cur.fetchall()
        conn.close()
        return ValidationResult(ok=True, message=f"EXPLAIN 校验通过, rows={len(rows)}")
    except Exception as exc:
        return ValidationResult(ok=False, error_code=E_EXPLAIN_FAIL, message=f"EXPLAIN 失败: {exc}")
