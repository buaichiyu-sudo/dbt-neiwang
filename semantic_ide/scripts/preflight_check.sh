#!/usr/bin/env bash
# Semantic-IDE intranet preflight checker
# Usage:
#   bash scripts/preflight_check.sh [--env-file .env]

set -u

ENV_FILE=".env"
if [[ "${1:-}" == "--env-file" && -n "${2:-}" ]]; then
  ENV_FILE="$2"
fi

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PASS=0
WARN=0
FAIL=0

ok() {
  echo -e "${GREEN}✅ PASS${NC} $1"
  PASS=$((PASS + 1))
}
warn() {
  echo -e "${YELLOW}⚠️  WARN${NC} $1"
  WARN=$((WARN + 1))
}
fail() {
  echo -e "${RED}❌ FAIL${NC} $1"
  FAIL=$((FAIL + 1))
}

section() {
  echo
  echo "==================== $1 ===================="
}

section "1) Python runtime & dependencies"
if command -v python >/dev/null 2>&1; then
  ok "python found: $(python --version 2>&1)"
else
  fail "python not found"
fi

python - <<'PY' >/tmp/semantic_ide_depcheck.txt 2>&1
import importlib
mods = ["streamlit", "sqlglot", "yaml", "jsonschema", "requests", "pandas", "pymysql"]
missing = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception:
        missing.append(m)
if missing:
    print("MISSING:" + ",".join(missing))
    raise SystemExit(1)
print("OK")
PY
if [[ $? -eq 0 ]]; then
  ok "Python dependencies are importable"
else
  fail "Missing Python deps: $(cat /tmp/semantic_ide_depcheck.txt)"
fi

section "2) dbt toolchain"
if command -v dbt >/dev/null 2>&1; then
  ok "dbt cli found: $(dbt --version | head -n 1)"
else
  fail "dbt cli not found (need dbt-core + adapter + dbt-codegen)"
fi

if dbt --version >/tmp/semantic_ide_dbt_version.txt 2>&1; then
  if grep -qi "codegen" /tmp/semantic_ide_dbt_version.txt; then
    ok "dbt-codegen appears in dbt package list"
  else
    warn "dbt-codegen not shown in dbt --version output (verify installation)"
  fi
else
  warn "Cannot execute dbt --version; skip plugin verification"
fi

section "3) env variables & skills direct mode"
required_vars=(QWEN_API_BASE QWEN_API_KEY DBT_PROJECT_DIR DBT_PROFILES_DIR)
for v in "${required_vars[@]}"; do
  if [[ -n "${!v:-}" ]]; then
    ok "$v is set"
  else
    fail "$v is empty"
  fi
done

if [[ "${DBT_AGENT_SKILLS_MODE:-direct}" == "direct" ]]; then
  if [[ -z "${DBT_AGENT_SKILLS_PATH:-}" ]]; then
    fail "DBT_AGENT_SKILLS_MODE=direct but DBT_AGENT_SKILLS_PATH is empty"
  elif [[ ! -d "${DBT_AGENT_SKILLS_PATH}" ]]; then
    fail "DBT_AGENT_SKILLS_PATH not found: ${DBT_AGENT_SKILLS_PATH}"
  else
    ok "DBT_AGENT_SKILLS_PATH exists: ${DBT_AGENT_SKILLS_PATH}"
  fi

  skills_files="${DBT_AGENT_SKILLS_FILES:-README.md}"
  IFS=',' read -r -a files <<< "$skills_files"
  for f in "${files[@]}"; do
    f_trim=$(echo "$f" | xargs)
    if [[ -f "${DBT_AGENT_SKILLS_PATH}/${f_trim}" ]]; then
      ok "skills file exists: ${f_trim}"
    else
      fail "skills file missing: ${DBT_AGENT_SKILLS_PATH}/${f_trim}"
    fi
  done
else
  warn "DBT_AGENT_SKILLS_MODE=${DBT_AGENT_SKILLS_MODE:-unset}; not using direct mode"
fi

section "4) API & Doris connectivity (best effort)"
if [[ -n "${QWEN_API_BASE:-}" ]]; then
  if curl -sS -m 5 -o /tmp/semantic_ide_qwen_head.txt "${QWEN_API_BASE}" >/dev/null 2>&1; then
    ok "QWEN_API_BASE reachable"
  else
    warn "QWEN_API_BASE not reachable from this host"
  fi
else
  fail "QWEN_API_BASE is empty"
fi

python - <<'PY' >/tmp/semantic_ide_doris_check.txt 2>&1
import os
import pymysql
host=os.getenv("DORIS_HOST","")
port=int(os.getenv("DORIS_PORT","9030"))
user=os.getenv("DORIS_USER","")
pwd=os.getenv("DORIS_PASSWORD","")
db=os.getenv("DORIS_DATABASE","")
if not all([host,user,db]):
    raise SystemExit("missing doris env")
conn=pymysql.connect(host=host,port=port,user=user,password=pwd,database=db,connect_timeout=5,read_timeout=8,write_timeout=8)
with conn.cursor() as cur:
    cur.execute("SELECT 1")
    cur.fetchone()
conn.close()
print("OK")
PY
if [[ $? -eq 0 ]]; then
  ok "Doris connectivity check passed"
else
  warn "Doris connectivity check failed: $(cat /tmp/semantic_ide_doris_check.txt)"
fi

section "5) dbt-codegen smoke & app import"
if [[ -n "${DBT_PROJECT_DIR:-}" && -n "${DBT_PROFILES_DIR:-}" ]]; then
  dbt run-operation generate_model_yaml --args '{"model_names": ["__dummy__"]}' \
    --project-dir "${DBT_PROJECT_DIR}" --profiles-dir "${DBT_PROFILES_DIR}" >/tmp/semantic_ide_codegen_check.txt 2>&1
  if [[ $? -eq 0 ]]; then
    ok "dbt-codegen command executed successfully"
  else
    warn "dbt-codegen smoke failed (check project/profile/permissions): $(tail -n 3 /tmp/semantic_ide_codegen_check.txt | tr '\n' ' ')"
  fi
else
  fail "DBT_PROJECT_DIR / DBT_PROFILES_DIR not set"
fi

python - <<'PY' >/tmp/semantic_ide_import_check.txt 2>&1
import importlib
importlib.import_module("app")
print("OK")
PY
if [[ $? -eq 0 ]]; then
  ok "Streamlit app module import check passed"
else
  fail "App import check failed: $(cat /tmp/semantic_ide_import_check.txt)"
fi

section "Summary"
echo "PASS=${PASS}  WARN=${WARN}  FAIL=${FAIL}"
if [[ $FAIL -gt 0 ]]; then
  echo -e "${RED}Preflight result: RED${NC}"
  exit 2
elif [[ $WARN -gt 0 ]]; then
  echo -e "${YELLOW}Preflight result: YELLOW${NC}"
  exit 1
else
  echo -e "${GREEN}Preflight result: GREEN${NC}"
  exit 0
fi
