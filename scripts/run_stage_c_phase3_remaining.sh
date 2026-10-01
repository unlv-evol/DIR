#!/usr/bin/env bash
set -u
set -o pipefail

ROOT="$(git rev-parse --show-toplevel)" || exit 1
cd "$ROOT" || exit 1

STATE_SCRIPT="scripts/stage_c_phase3_state.py"
LOG="cases/manifests/stage_c_v2_phase3_execution.log"
REMAINING_FILE="$(mktemp "${TMPDIR:-/tmp}/dir-stage-c-phase3.XXXXXX")"
trap 'rm -f "$REMAINING_FILE"' EXIT
trap 'printf "\nInterrupted safely. Completed outputs are preserved; rerun this script to resume.\n" | tee -a "$LOG"; exit 130' INT TERM

log() {
    printf '%s\n' "$*" | tee -a "$LOG"
}

log "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Phase 3 resume check"

# A nonzero configuration check is systemic, so stop before any API call.
PYTHONPATH=src python3 pipeline/stage_c/run.py --check-config --input-version v2 \
    2>&1 | tee -a "$LOG"
config_exit=${PIPESTATUS[0]}
if [ "$config_exit" -ne 0 ]; then
    log "Systemic configuration failure; no cases executed."
    exit "$config_exit"
fi

python3 "$STATE_SCRIPT" --summary 2>&1 | tee -a "$LOG"
python3 "$STATE_SCRIPT" --remaining > "$REMAINING_FILE" || exit 1
remaining_count="$(wc -l < "$REMAINING_FILE" | tr -d ' ')"

log "Exact remaining case IDs (${remaining_count}):"
if [ "$remaining_count" -eq 0 ]; then
    log "(none)"
    python3 "$STATE_SCRIPT" --validate-coverage 2>&1 | tee -a "$LOG"
    exit ${PIPESTATUS[0]}
fi
cat "$REMAINING_FILE" | tee -a "$LOG"

while IFS= read -r case_id; do
    [ -n "$case_id" ] || continue
    accounted="$(python3 "$STATE_SCRIPT" --accounted-count)" || exit 1
    position=$((accounted + 1))
    command="python3 pipeline/stage_c/run.py --case-id $case_id --input-version v2 --live"
    log "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [$position/122] START $case_id"
    log "command: $command"

    PYTHONPATH=src python3 pipeline/stage_c/run.py \
        --case-id "$case_id" \
        --input-version v2 \
        --live 2>&1 | tee -a "$LOG"
    case_exit=${PIPESTATUS[0]}

    state="$(python3 "$STATE_SCRIPT" --status "$case_id")" || exit 1
    log "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [$position/122] END $case_id exit=$case_exit"
    log "result: $state"

    # A preserved record is an explicit isolated disposition, even if the
    # process returned nonzero. Absence of a record is a systemic stop.
    if printf '%s' "$state" | grep -q '"accounted": true'; then
        continue
    fi
    log "Systemic execution failure: no Stage C V2 disposition was preserved."
    exit "${case_exit:-1}"
done < "$REMAINING_FILE"

python3 "$STATE_SCRIPT" --validate-coverage 2>&1 | tee -a "$LOG"
exit ${PIPESTATUS[0]}
