from core.pipeline.guardrails import enforce_partition_filter


def test_guardrail_pass_with_dt():
    sql = "select * from t where dt='2026-04-28'"
    result = enforce_partition_filter(sql)
    assert result.ok


def test_guardrail_fail_without_dt():
    sql = "select * from t where station_id='A001'"
    result = enforce_partition_filter(sql)
    assert not result.ok


def test_guardrail_fail_subquery_without_dt():
    sql = """
    select *
    from (
      select station_id from t where station_id='A001'
    ) s
    where dt='2026-04-28'
    """
    result = enforce_partition_filter(sql)
    assert not result.ok


def test_guardrail_pass_with_dbt_ref_template():
    sql = "select * from {{ ref('dwd_orders') }} where dt='2026-04-28'"
    result = enforce_partition_filter(sql)
    assert result.ok
