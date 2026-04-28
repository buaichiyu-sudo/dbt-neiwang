from core.pipeline.dbt_sql_renderer import render_dbt_sql_for_validation


def test_render_dbt_macros_for_validation():
    sql = """
    {{ config(materialized='table') }}
    select *
    from {{ ref('dws_charge_order_di') }}
    where dt = '{{ var("biz_date") }}'
    """

    rendered = render_dbt_sql_for_validation(sql)

    assert "{{" not in rendered
    assert "dws_charge_order_di" in rendered
    assert "biz_date" in rendered


def test_render_source_macro_for_validation():
    sql = "select * from {{ source('ods', 'order_di') }}"
    rendered = render_dbt_sql_for_validation(sql)
    assert "ods.order_di" in rendered
