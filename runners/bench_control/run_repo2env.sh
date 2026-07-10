#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib/bench_common.sh"
bench_init repo2env

REPO2ENV_ROOT="${REPO2ENV_ROOT:-$NIPS_ROOT/repo2env}"
REPO2ENV_MODE="${REPO2ENV_MODE:-agentic_tiny}"
REPO2ENV_MODEL="${REPO2ENV_MODEL:-$MODEL_NAME}"
bench_require_path "$REPO2ENV_ROOT" "repo2env checkout"

cd "$REPO2ENV_ROOT"
export PYTHONPATH="$REPO2ENV_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

if [[ "$REPO2ENV_MODE" == "diagnostic_offline" ]]; then
  out="$BENCH_RUN_DIR/offline-e2e-smoke"
  bench_run bash scripts/benchmark_offline_e2e_smoke.sh "$out" 2>&1 | tee "$BENCH_RUN_DIR/repo2env_diagnostic.log"
  bench_finish "$out/yield.json"
  exit 0
fi

if [[ "$REPO2ENV_MODE" == "small_real_agentic" ]]; then
  out="$BENCH_RUN_DIR/small-real-agentic"
  instances="${REPO2ENV_INSTANCES:-.repo2env/benchmarks/small-real-dry-run-cached/suite/instances.jsonl}"
  suite="${REPO2ENV_SUITE:-.repo2env/benchmarks/small-real-dry-run-cached/suite/suite.json}"
  candidate_report="${REPO2ENV_CANDIDATE_REPORT:-.repo2env/benchmarks/small-real-dry-run-cached/candidate_report.json}"
  suite_report="${REPO2ENV_SUITE_REPORT:-.repo2env/benchmarks/small-real-dry-run-cached/suite/build_report.json}"
  mkdir -p "$out"
  export REPO2ENV_OPENAI_API_KEY="${REPO2ENV_OPENAI_API_KEY:-$OPENAI_API_KEY}"
  export REPO2ENV_OPENAI_BASE_URL="${REPO2ENV_OPENAI_BASE_URL:-$OPENAI_BASE_URL}"

  cmd=(
    python -m repo2env.cli bench run
    --instances "$instances"
    --suite "$suite"
    --out "$out/run"
    --workspace "$out/workspace"
    --worlds "$out/worlds"
    --diagnostic-validation
    --eval-mode container
    --acceptance-level container
    --workers "${REPO2ENV_WORKERS:-$MAX_CONCURRENCY}"
    --docker-timeout "${REPO2ENV_DOCKER_TIMEOUT:-1800}"
    --eval-timeout "${REPO2ENV_EVAL_TIMEOUT:-300}"
    --strict-api
    --allow-insecure-llm-endpoint
    --agentic-env-base-url "$REPO2ENV_OPENAI_BASE_URL"
    --agentic-env-session
    --agentic-env-session-model "$REPO2ENV_MODEL"
    --agentic-env-session-max-trials "${REPO2ENV_MAX_TRIALS:-3}"
    --agentic-env-session-max-setup-steps "${REPO2ENV_MAX_SETUP_STEPS:-20}"
    --agentic-env-session-max-verify-steps "${REPO2ENV_MAX_VERIFY_STEPS:-10}"
    --agentic-env-session-network "${REPO2ENV_NETWORK:-diagnostic}"
    --resume
    --retry-failed
    --max-retries "${REPO2ENV_MAX_RETRIES:-0}"
  )
  printf '%q ' "${cmd[@]}" | tee "$BENCH_RUN_DIR/command.sh"
  printf '\n' | tee -a "$BENCH_RUN_DIR/command.sh"
  "${cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/repo2env_small_real_agentic.log"

  summary_cmd=(
    python -m repo2env.cli bench summary
    --results "$out/run/results.jsonl"
    --instances "$instances"
    --suite "$suite"
    --out "$out/run"
  )
  "${summary_cmd[@]}" 2>&1 | tee -a "$BENCH_RUN_DIR/repo2env_small_real_agentic.log"

  qualify_cmd=(
    python -m repo2env.cli bench qualify
    --instances "$instances"
    --results "$out/run/results.jsonl"
    --suite "$suite"
    --min-level L3_smoke_tests
    --out "$out/qualified"
    --force
  )
  "${qualify_cmd[@]}" 2>&1 | tee -a "$BENCH_RUN_DIR/repo2env_small_real_agentic.log"

  yield_cmd=(
    python -m repo2env.cli bench yield
    --candidate-report "$candidate_report"
    --suite-report "$suite_report"
    --run-summary "$out/run/summary.json"
    --qualification-report "$out/qualified/qualification_report.json"
    --out "$out/yield.json"
  )
  "${yield_cmd[@]}" 2>&1 | tee -a "$BENCH_RUN_DIR/repo2env_small_real_agentic.log"

  bench_finish "$out/yield.json"
  exit 0
fi

fixture="$BENCH_RUN_DIR/fixture/tiny-python"
worlds="$BENCH_RUN_DIR/worlds"
workspace="$BENCH_RUN_DIR/workspace"
mkdir -p "$fixture/tests" "$worlds" "$workspace"
cat >"$fixture/calc.py" <<'PY'
def add(a, b):
    return a + b
PY
cat >"$fixture/tests/test_calc.py" <<'PY'
from calc import add


def test_add():
    assert add(2, 3) == 5
PY
cat >"$fixture/pyproject.toml" <<'TOML'
[project]
name = "repo2env-bench-tiny"
version = "0.0.1"
TOML

cmd=(
  python -m repo2env.cli ingest "$fixture"
  --workspace "$workspace"
  --out "$worlds"
  --force
  --skip-issue-discovery
  --agentic-env-session
  --agentic-env-session-model "$REPO2ENV_MODEL"
  --agentic-env-session-max-trials "${REPO2ENV_MAX_TRIALS:-1}"
  --agentic-env-session-max-setup-steps "${REPO2ENV_MAX_SETUP_STEPS:-4}"
  --agentic-env-session-max-verify-steps "${REPO2ENV_MAX_VERIFY_STEPS:-3}"
  --agentic-env-session-network "${REPO2ENV_NETWORK:-disabled}"
  --agentic-env-base-url "$OPENAI_BASE_URL"
  --agentic-env-reasoning-effort "$OPENAI_REASONING_EFFORT"
  --allow-insecure-llm-endpoint
  --docker-timeout "${REPO2ENV_DOCKER_TIMEOUT:-600}"
  --eval-timeout "${REPO2ENV_EVAL_TIMEOUT:-180}"
  --eval-mode container
  --acceptance-level container
  --clean-replay
  --clean-replay-timeout "${REPO2ENV_CLEAN_REPLAY_TIMEOUT:-300}"
  --clean-replay-build-timeout "${REPO2ENV_CLEAN_REPLAY_BUILD_TIMEOUT:-600}"
  --allow-rejected-exit-zero
)

printf '%q ' "${cmd[@]}" | tee "$BENCH_RUN_DIR/command.sh"
printf '\n' | tee -a "$BENCH_RUN_DIR/command.sh"
"${cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/repo2env_agentic.log"

world="$(find "$worlds" -mindepth 1 -maxdepth 1 -type d | sort | head -n 1 || true)"
if [[ -z "$world" ]]; then
  echo "No repo2env world produced under $worlds" >&2
  exit 4
fi

python - "$world" "$BENCH_RUN_DIR/summary.json" <<'PY'
import json
import sys
from pathlib import Path

world = Path(sys.argv[1])
out = Path(sys.argv[2])

def load(rel):
    path = world / rel
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        return {"load_error": type(exc).__name__}

payload = {
    "world": str(world),
    "acceptance": load("acceptance_report.json"),
    "agentic_session": load("runtime/agentic_session_result.json"),
    "setup_sh": str(world / "build/setup.sh"),
    "test_sh": str(world / "build/test.sh"),
}
out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
print(out)
PY

bench_finish "$BENCH_RUN_DIR/summary.json"
