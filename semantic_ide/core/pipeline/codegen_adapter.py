import subprocess


def generate_schema_skeleton(table_name: str, project_dir: str, profiles_dir: str, mock_mode: bool = True) -> str:
    """Call dbt-codegen and return real skeleton.

    In non-mock mode, failures are raised to stop the pipeline.
    In mock mode, failures fall back to a tiny stub skeleton for local development.
    """
    cmd = [
        "dbt",
        "run-operation",
        "generate_model_yaml",
        "--args",
        f"{{\"model_names\": [\"{table_name}\"]}}",
        "--project-dir",
        project_dir,
        "--profiles-dir",
        profiles_dir,
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout
    except Exception as exc:
        if not mock_mode:
            raise RuntimeError(f"dbt-codegen 执行失败: {exc}") from exc

        return (
            f"# MOCK_FALLBACK: dbt-codegen failed: {exc}\n"
            "version: 2\nmodels:\n"
            f"  - name: {table_name}\n"
            "    description: TODO\n"
            "    columns: []\n"
        )
