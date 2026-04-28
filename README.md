# dbt-neiwang

## 推荐入口（内网联调）

优先使用 modular 版本：

```bash
cd semantic_ide
streamlit run app.py
```

当前默认以 `DBT_AGENT_SKILLS_MODE=direct` 方式接入 dbt-agent-skills（从本地 skills 路径直接读取原始文件）。

## 单文件版本

`semantic_ide_phase1.py` 保留为 demo/快速验证入口，不作为默认生产入口。
