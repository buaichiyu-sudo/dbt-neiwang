from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os


class Settings(BaseModel):
    qwen_api_base: str = Field(default="")
    qwen_api_key: str = Field(default="")
    qwen_model: str = Field(default="qwen3.5")

    dbt_project_dir: str = Field(default=".")
    dbt_profiles_dir: str = Field(default="~/.dbt")

    doris_host: str = Field(default="")
    doris_port: int = Field(default=9030)
    doris_user: str = Field(default="")
    doris_password: str = Field(default="")
    doris_database: str = Field(default="")

    mock_mode: bool = Field(default=True)

    # dbt-agent-skills loading mode
    dbt_agent_skills_mode: str = Field(default="direct")
    dbt_agent_skills_path: str = Field(default="")
    dbt_agent_skills_files: str = Field(default="README.md")

    @property
    def project_root(self) -> Path:
        return Path(self.dbt_project_dir).expanduser().resolve()


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        qwen_api_base=os.getenv("QWEN_API_BASE", ""),
        qwen_api_key=os.getenv("QWEN_API_KEY", ""),
        qwen_model=os.getenv("QWEN_MODEL", "qwen3.5"),
        dbt_project_dir=os.getenv("DBT_PROJECT_DIR", "."),
        dbt_profiles_dir=os.getenv("DBT_PROFILES_DIR", "~/.dbt"),
        doris_host=os.getenv("DORIS_HOST", ""),
        doris_port=int(os.getenv("DORIS_PORT", "9030")),
        doris_user=os.getenv("DORIS_USER", ""),
        doris_password=os.getenv("DORIS_PASSWORD", ""),
        doris_database=os.getenv("DORIS_DATABASE", ""),
        mock_mode=os.getenv("SEMANTIC_IDE_MOCK", "true").lower() == "true",
        dbt_agent_skills_mode=os.getenv("DBT_AGENT_SKILLS_MODE", "direct"),
        dbt_agent_skills_path=os.getenv("DBT_AGENT_SKILLS_PATH", ""),
        dbt_agent_skills_files=os.getenv("DBT_AGENT_SKILLS_FILES", "README.md"),
    )
