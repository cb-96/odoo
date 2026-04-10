#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# Sports Federation CI – run Odoo module tests in an isolated container.
#
# Usage:
#   bash addons/ci/run_tests.sh              # test all modules
#   bash addons/ci/run_tests.sh --module sports_federation_base
#   bash addons/ci/run_tests.sh --keep       # keep containers for debugging
#
# Requirements: docker compose v2
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.ci.yaml"
ENV_FILE="$SCRIPT_DIR/.env"
EXAMPLE_ENV_FILE="$SCRIPT_DIR/.env.example"
GENERATED_CONF="$SCRIPT_DIR/odoo-ci.generated.conf"

if [[ -f "$ENV_FILE" ]]; then
  LOADED_ENV_FILE="$ENV_FILE"
elif [[ -f "$EXAMPLE_ENV_FILE" ]]; then
  LOADED_ENV_FILE="$EXAMPLE_ENV_FILE"
else
  echo "Missing CI environment file. Create $ENV_FILE from $EXAMPLE_ENV_FILE." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$LOADED_ENV_FILE"
set +a

: "${CI_PROJECT_NAME:=sf_ci}"
: "${CI_POSTGRES_USER:=odoo}"
: "${CI_POSTGRES_PASSWORD:=change_me}"
: "${CI_POSTGRES_DB:=postgres}"
: "${CI_ODOO_DB_NAME:=odoo_ci_test}"
: "${CI_ODOO_DB_HOST:=ci-db}"
: "${CI_ODOO_DB_PORT:=5432}"

PROJECT_NAME="$CI_PROJECT_NAME"

cat > "$GENERATED_CONF" <<EOF
[options]
db_host = ${CI_ODOO_DB_HOST}
db_port = ${CI_ODOO_DB_PORT}
db_user = ${CI_POSTGRES_USER}
db_password = ${CI_POSTGRES_PASSWORD}

addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
data_dir = /var/lib/odoo

list_db = False
without_demo = True
log_level = info
EOF

# ── Topological install order (dependency-safe) ──────────────────────
ALL_MODULES=(
  sports_federation_base
  sports_federation_rules
  sports_federation_people
  sports_federation_tournament
  sports_federation_standings
  sports_federation_venues
  sports_federation_result_control
  sports_federation_portal
  sports_federation_rosters
  sports_federation_competition_engine
  sports_federation_officiating
  sports_federation_discipline
  sports_federation_governance
  sports_federation_notifications
  sports_federation_import_tools
  sports_federation_finance_bridge
  sports_federation_compliance
  sports_federation_public_site
  sports_federation_reporting
)

# ── CLI parsing ──────────────────────────────────────────────────────
MODULES=()
KEEP=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --module|-m)  MODULES+=("$2"); shift 2 ;;
    --keep|-k)    KEEP=true; shift ;;
    *)            echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ ${#MODULES[@]} -eq 0 ]]; then
  MODULES=("${ALL_MODULES[@]}")
fi

MODULE_CSV=$(IFS=,; echo "${MODULES[*]}")

# ── Log directory ────────────────────────────────────────────────────
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="$SCRIPT_DIR/logs/$TIMESTAMP"
mkdir -p "$LOG_DIR"

RAW_LOG="$LOG_DIR/raw.log"
SUMMARY_LOG="$LOG_DIR/summary.log"
ERRORS_LOG="$LOG_DIR/errors.log"

echo "=== SF CI Run – $TIMESTAMP ===" | tee "$SUMMARY_LOG"
echo "Modules: $MODULE_CSV" | tee -a "$SUMMARY_LOG"
echo "Config:  $LOADED_ENV_FILE" | tee -a "$SUMMARY_LOG"
echo "Logs:    $LOG_DIR" | tee -a "$SUMMARY_LOG"
echo "────────────────────────────────────────────" | tee -a "$SUMMARY_LOG"

# ── Bring up isolated environment ────────────────────────────────────
echo "[CI] Starting containers …"
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d ci-db
echo "[CI] Waiting for Postgres to be healthy …"
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --wait ci-db

# Create the test database
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T ci-db \
  psql -U "$CI_POSTGRES_USER" -d "$CI_POSTGRES_DB" -c "SELECT 1 FROM pg_database WHERE datname='$CI_ODOO_DB_NAME'" \
  | grep -q 1 || \
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T ci-db \
  psql -U "$CI_POSTGRES_USER" -d "$CI_POSTGRES_DB" -c "CREATE DATABASE \"$CI_ODOO_DB_NAME\" OWNER \"$CI_POSTGRES_USER\";"

# ── Run tests ────────────────────────────────────────────────────────
echo "[CI] Installing & testing: $MODULE_CSV"
EXIT_CODE=0

# Build test tags to only run federation module tests (skip base Odoo tests)
TEST_TAGS=""
for mod in "${MODULES[@]}"; do
  if [[ -n "$TEST_TAGS" ]]; then
    TEST_TAGS="$TEST_TAGS,$mod"
  else
    TEST_TAGS="$mod"
  fi
done

docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" run --rm \
  ci-odoo \
  --stop-after-init --test-enable --test-tags="$TEST_TAGS" \
  -d "$CI_ODOO_DB_NAME" -i "$MODULE_CSV" \
  2>&1 | tee "$RAW_LOG" || EXIT_CODE=$?

# ── Parse results ────────────────────────────────────────────────────
grep -iE "(FAIL|ERROR|CRITICAL|Traceback|raise.*Error)" "$RAW_LOG" > "$ERRORS_LOG" 2>/dev/null || true
ERROR_COUNT=$(wc -l < "$ERRORS_LOG")

# Check for test summary lines
TESTS_PASSED=$(grep -c "^ok$\|: ok$\|PASS" "$RAW_LOG" 2>/dev/null || echo "0")
TESTS_FAILED=$(grep -c "FAIL\|ERROR" "$ERRORS_LOG" 2>/dev/null || echo "0")

{
  echo ""
  echo "════════════════════════════════════════════"
  echo "  RESULTS"
  echo "════════════════════════════════════════════"
  echo "  Exit code:     $EXIT_CODE"
  echo "  Error lines:   $ERROR_COUNT"
  echo "  Tests passed:  ~$TESTS_PASSED"
  echo "  Tests failed:  ~$TESTS_FAILED"
  echo "════════════════════════════════════════════"
} | tee -a "$SUMMARY_LOG"

if [[ $EXIT_CODE -ne 0 ]]; then
  echo ""
  echo "[CI] ❌ TESTS FAILED — see $ERRORS_LOG"
  echo "Last 30 lines of errors:"
  tail -30 "$ERRORS_LOG"
fi

# ── Cleanup ──────────────────────────────────────────────────────────
if [[ "$KEEP" == "false" ]]; then
  echo ""
  echo "[CI] Tearing down containers …"
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
  rm -f "$GENERATED_CONF"
else
  echo ""
  echo "[CI] --keep: containers left running (project: $PROJECT_NAME)"
  echo "     To stop: docker compose -p $PROJECT_NAME -f $COMPOSE_FILE down -v"
fi

exit "$EXIT_CODE"
