import pandas as pd

from core.config import Settings


def _normalize_limit_sql(sql: str, limit: int = 10) -> str:
    lowered = sql.lower()
    if " limit " in lowered:
        return sql
    return f"{sql.rstrip().rstrip(';')} LIMIT {limit}"


def preview_sql_result(sql: str, settings: Settings, limit: int = 10) -> pd.DataFrame:
    """Run LIMIT preview on Doris in non-mock mode; otherwise return mock dataframe."""
    if settings.mock_mode:
        return pd.DataFrame(
            {
                "dt": ["2026-04-27", "2026-04-28"],
                "station_id": ["A001", "A001"],
                "charge_efficiency": [0.82, 0.85],
            }
        )

    import pymysql  # type: ignore

    preview_sql = _normalize_limit_sql(sql, limit=limit)
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
    try:
        return pd.read_sql(preview_sql, conn)
    finally:
        conn.close()
