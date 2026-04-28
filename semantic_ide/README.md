# Semantic-IDE MVP (Modular)

## 1. 安装
```bash
cd semantic_ide
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

> 生产联调时还需本地安装 dbt 工具链：`dbt-core`、对应 adapter、`dbt-codegen`。

## 2. 启动
```bash
streamlit run app.py
```

## 3. 使用流程
1. 输入物理表名 + 多模态业务输入（自然语言/旧SQL/Excel口径）。
2. 点击“解析意图”，系统输出 Intent JSON。
3. 若复杂度高，阻断 SQL 生成并输出 DWD 建议。
4. 点击“生成语义模型”，系统执行 codegen + LLM + schema 校验。
5. 点击“预览数据”执行 LIMIT 10 查询（mock 模式返回样例数据）。
6. 点击“落盘”执行 AST + EXPLAIN 并写入 `./models/semantic_ide/`（默认不覆盖同名文件，需手动勾选覆盖）。

## 4. dbt-agent-skills 直接接入
默认使用 `direct` 模式，不再只使用蒸馏提示词：

```env
DBT_AGENT_SKILLS_MODE=direct
DBT_AGENT_SKILLS_PATH=/path/to/dbt-agent-skills
DBT_AGENT_SKILLS_FILES=README.md,examples/metricflow_prompt.md
```

- `direct`：直接读取 skills 源文件并拼接为 system prompt。
- `distilled`：仅用于离线回退。

## 5. 关键策略
- 非 mock 模式下，`dbt-codegen` 失败会直接中断流程（不再静默降级）。
- AST 护栏会检查主查询与子查询中的分区过滤（默认 `dt`）。
- EXPLAIN 在非 mock 模式下会真实连接 Doris 执行。
- Intent 输出会按 `assets/schemas/intent.schema.json` 进行 JSON Schema 校验。
- 右侧会显示 Prompt Bundle 版本与当前接入模式，便于审计。

## 6. 内网上线前红绿灯自检

```bash
cd semantic_ide
bash scripts/preflight_check.sh --env-file .env
```

- 退出码 `0`: GREEN
- 退出码 `1`: YELLOW（有告警）
- 退出码 `2`: RED（有阻断问题）


## 7. 内网 Cline 安装调试说明

详见：`INTRANET_SETUP_CLINE.md`（包含安装、.env 模板、红绿灯检查、联调顺序、常见问题）。
