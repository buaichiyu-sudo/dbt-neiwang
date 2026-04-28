# Semantic-IDE 内网安装与调试手册（Cline 版）

> 目标：让你在内网环境借助 Cline 进行安装、联调、排障时，有一条可重复、低决策成本的执行路径。

## 0. 范围与入口

- 推荐入口：`semantic_ide/app.py`
- 单文件 `semantic_ide_phase1.py` 仅作 demo，不建议作为内网长期入口。

---

## 1. 前置依赖清单（必须确认）

### 1.1 Python 与包源
- Python 3.10+
- 内网 pip 镜像可访问
- 建议先验证：
  ```bash
  python --version
  pip --version
  pip config list
  ```

### 1.2 dbt 工具链
- `dbt-core`
- 对应数据库 adapter（按你们 Doris 接入策略）
- `dbt-codegen`
- `DBT_PROJECT_DIR` 对应的项目可执行 `dbt debug`

### 1.3 数据源与模型服务
- Qwen3.5 API（内网地址、密钥）
- Doris 只读账号（EXPLAIN + 预览查询）

### 1.4 skills 源文件（direct 模式）
- 本地可访问的 `dbt-agent-skills` 路径
- 至少一个可读文件（例如 `README.md`）

---

## 2. 推荐安装步骤（Cline 可逐条执行）

> 以下命令假设你已在仓库根目录。

```bash
cd semantic_ide
python -m venv .venv
source .venv/bin/activate

# 如果你们内网使用私有镜像，可先配置
# pip config set global.index-url <YOUR_INTRANET_PYPI>

pip install -r requirements.txt
cp .env.example .env
```

> 注意：`requirements.txt` 不包含 dbt 工具链，请按内网规范额外安装 `dbt-core + adapter + dbt-codegen`。

---

## 3. .env 最小可用配置模板

```env
QWEN_API_BASE=http://<内网qwen地址>
QWEN_API_KEY=<内网key>
QWEN_MODEL=qwen3.5

DBT_PROJECT_DIR=.
DBT_PROFILES_DIR=~/.dbt

DORIS_HOST=<doris_host>
DORIS_PORT=9030
DORIS_USER=<readonly_user>
DORIS_PASSWORD=<readonly_pwd>
DORIS_DATABASE=<db_name>

SEMANTIC_IDE_MOCK=false

DBT_AGENT_SKILLS_MODE=direct
DBT_AGENT_SKILLS_PATH=/path/to/dbt-agent-skills
DBT_AGENT_SKILLS_FILES=README.md,examples/metricflow_prompt.md
```

---

## 4. 上线前红绿灯检查（强烈建议）

```bash
cd semantic_ide
bash scripts/preflight_check.sh --env-file .env
```

退出码含义：
- `0` = GREEN：可进入联调
- `1` = YELLOW：可联调但存在风险项
- `2` = RED：先修复阻断项

---

## 5. Cline 联调顺序（建议）

1. `解析意图`：确认 Intent JSON 结构正确。
2. `生成语义模型`：确认 codegen + prompt 直连可运行。
3. `预览数据`：确认 Doris 读链路正常。
4. `落盘`：确认 AST + EXPLAIN + 文件写入成功。

建议首个验收用例：
- “统计昨日单站充电效率”

---

## 6. 常见问题速查

### A. `direct 模式需要 DBT_AGENT_SKILLS_PATH`
- 原因：未配置路径或路径不可访问。
- 处理：检查 `.env` 与文件权限。

### B. `dbt-codegen 执行失败`
- 原因：dbt 工具链缺失、profiles 配置错误、网络不可达。
- 处理：先执行 `dbt debug`，再单独执行 `dbt run-operation generate_model_yaml ...`。

### C. `EXPLAIN 失败`
- 原因：Doris 网络/账号权限/SQL 语法问题。
- 处理：用同账号先执行 `SELECT 1` 和 `EXPLAIN` 手工验证。

### D. `SQL 缺少 dt 分区过滤`
- 原因：AST 护栏拦截。
- 处理：修正生成 SQL 的 WHERE 条件。

### E. `pytest` 报缺模块
- 原因：依赖未从内网镜像成功安装。
- 处理：先修复 pip 镜像，再 `pip install -r requirements.txt`。

---

## 7. 建议补充到你们内网知识库的信息

- 你们真实的 `DBT_PROJECT_DIR` 与 `DBT_PROFILES_DIR` 标准路径。
- Doris 只读账号申请流程（最小权限策略）。
- Qwen API SLA、超时阈值、限流策略。
- 内网 PyPI 镜像地址与证书配置规范。
- dbt adapter 版本与升级窗口（避免和 dbt-core 版本冲突）。
