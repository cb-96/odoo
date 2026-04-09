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
PROJECT_NAME="sf_ci"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.ci.yaml"

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
echo "Logs:    $LOG_DIR" | tee -a "$SUMMARY_LOG"
echo "────────────────────────────────────────────" | tee -a "$SUMMARY_LOG"

# ── Bring up isolated environment ────────────────────────────────────
echo "[CI] Starting containers …"
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d ci-db
echo "[CI] Waiting for Postgres to be healthy …"
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --wait ci-db

# Create the test database
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T ci-db \
  psql -U odoo -d postgres -c "SELECT 1 FROM pg_database WHERE datname='odoo_ci_test'" \
  | grep -q 1 || \
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T ci-db \
  psql -U odoo -d postgres -c "CREATE DATABASE odoo_ci_test OWNER odoo;"

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
  -d odoo_ci_test -i "$MODULE_CSV" \
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
else
  echo ""
  echo "[CI] --keep: containers left running (project: $PROJECT_NAME)"
  echo "     To stop: docker compose -p $PROJECT_NAME -f $COMPOSE_FILE down -v"
fi

exit "$EXIT_CODE"
