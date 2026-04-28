from pathlib import Path

from core.prompts.dbt_skill_prompts import load_system_prompt


def test_prompt_loader_direct_mode(tmp_path: Path, monkeypatch):
    skills_root = tmp_path / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    (skills_root / "README.md").write_text("RULE_A", encoding="utf-8")
    (skills_root / "extra.md").write_text("RULE_B", encoding="utf-8")

    monkeypatch.setenv("DBT_AGENT_SKILLS_PATH", str(skills_root))
    monkeypatch.setenv("DBT_AGENT_SKILLS_FILES", "README.md,extra.md")

    text = load_system_prompt(mode="direct", repair=False)
    assert "RULE_A" in text
    assert "RULE_B" in text


def test_prompt_loader_distilled_mode():
    text = load_system_prompt(mode="distilled", repair=False)
    assert "SQL WHERE" in text
