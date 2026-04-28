from pathlib import Path

from core.errors import E_SINK_WRITE


def write_assets(
    project_root: Path,
    model_name: str,
    sql: str,
    yml: str,
    allow_overwrite: bool = False,
) -> tuple[bool, str]:
    try:
        target = project_root / "models" / "semantic_ide"
        target.mkdir(parents=True, exist_ok=True)
        sql_path = target / f"{model_name}.sql"
        yml_path = target / f"{model_name}.yml"

        if not allow_overwrite and (sql_path.exists() or yml_path.exists()):
            return False, "E_SINK_WRITE: 目标文件已存在，请勾选允许覆盖或更换模型名"

        sql_path.write_text(sql, encoding="utf-8")
        yml_path.write_text(yml, encoding="utf-8")
        return True, f"已落盘: {sql_path} | {yml_path}"
    except Exception as exc:
        return False, f"{E_SINK_WRITE}: {exc}"
