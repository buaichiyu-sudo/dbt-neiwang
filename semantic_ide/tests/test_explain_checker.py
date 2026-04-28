import sys
import types

from core.config import Settings
from core.pipeline.explain_checker import run_explain


class _FakeCursor:
    def __init__(self):
        self.executed_sql = None

    def execute(self, sql):
        self.executed_sql = sql

    def fetchall(self):
        return [("ok",)]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self):
        self.cursor_obj = _FakeCursor()

    def cursor(self):
        return self.cursor_obj

    def close(self):
        pass


def test_run_explain_renders_dbt_macros_before_executing(monkeypatch):
    fake_conn = _FakeConnection()

    fake_pymysql = types.SimpleNamespace(connect=lambda **kwargs: fake_conn)
    monkeypatch.setitem(sys.modules, "pymysql", fake_pymysql)

    settings = Settings(
        mock_mode=False,
        doris_host="127.0.0.1",
        doris_user="root",
        doris_database="demo",
    )
    result = run_explain("select * from {{ ref('fct_orders') }} where dt='2026-04-28'", settings)

    assert result.ok
    assert "{{" not in fake_conn.cursor_obj.executed_sql
    assert "fct_orders" in fake_conn.cursor_obj.executed_sql
