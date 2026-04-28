from pathlib import Path

from core.pipeline.sink_writer import write_assets


def test_sink_writer_no_overwrite(tmp_path: Path):
    project_root = tmp_path
    model = "ads_demo"
    sql = "select 1"
    yml = "version: 2\nmodels: []"

    ok1, _ = write_assets(project_root, model, sql, yml, allow_overwrite=False)
    ok2, msg2 = write_assets(project_root, model, sql, yml, allow_overwrite=False)

    assert ok1 is True
    assert ok2 is False
    assert "已存在" in msg2
