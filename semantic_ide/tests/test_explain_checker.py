import sys
import types

from core.config import Settings
from core.pipeline.explain_checker import run_explain


class _DummyCursor:
    def __init__(self):
        self.executed = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql: str):
        self.executed = sql

    def fetchall(self):
        return [("ok",)]


class _DummyConn:
    def __init__(self, cursor_obj: _DummyCursor):
        self._cursor_obj = cursor_obj

    def cursor(self):
        return self._cursor_obj

    def close(self):
        return None


def test_explain_renders_dbt_macros(monkeypatch):
    cursor_obj = _DummyCursor()

    def _connect(**kwargs):
        return _DummyConn(cursor_obj)

    pymysql_mod = types.SimpleNamespace(connect=_connect)
    monkeypatch.setitem(sys.modules, "pymysql", pymysql_mod)

    settings = Settings(
        mock_mode=False,
        doris_host="127.0.0.1",
        doris_user="root",
        doris_database="test",
    )

    sql = "select * from {{ ref('dws_charge_order_di') }} where dt='2026-04-28'"
    result = run_explain(sql, settings)

    assert result.ok
    assert "{{ ref(" not in cursor_obj.executed
    assert "EXPLAIN select * from dws_charge_order_di" in cursor_obj.executed
