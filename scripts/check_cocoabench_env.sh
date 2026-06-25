#!/usr/bin/env bash
set -u

COCOA_ROOT="${COCOA_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent}"
COCOA_CONDA_PY="${COCOA_CONDA_PY:-/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/cocoa/bin/python3.13}"
COCOA_EXPECTED_UV_PY_ROOT="${COCOA_EXPECTED_UV_PY_ROOT:-/root/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu}"
UV_BIN="${UV_BIN:-/root/.local/bin/uv}"
TIMEOUT_BIN="${TIMEOUT_BIN:-timeout}"
TIMEOUT_S="${TIMEOUT_S:-10}"

failures=0

section() {
  printf '\n== %s ==\n' "$1"
}

mark_fail() {
  failures=$((failures + 1))
  printf 'FAIL: %s\n' "$1"
}

run_bounded() {
  if command -v "$TIMEOUT_BIN" >/dev/null 2>&1; then
    "$TIMEOUT_BIN" "$TIMEOUT_S" "$@"
  else
    "$@"
  fi
}

print_path() {
  local path="$1"
  if [[ -e "$path" || -L "$path" ]]; then
    ls -ld "$path"
    if [[ -L "$path" ]]; then
      printf 'readlink=%s\n' "$(readlink "$path" 2>/dev/null || true)"
      printf 'realpath=%s\n' "$(readlink -f "$path" 2>/dev/null || true)"
    fi
  else
    printf 'missing %s\n' "$path"
  fi
}

check_python() {
  local label="$1"
  local py="$2"
  section "$label"
  print_path "$py"
  if [[ ! -x "$py" ]]; then
    mark_fail "$label is not executable: $py"
    return
  fi
  run_bounded "$py" --version || mark_fail "$label --version failed"
  run_bounded "$py" - <<'PY' || mark_fail "$label introspection failed"
import site
import sys
print("executable", sys.executable)
print("version", sys.version.replace("\n", " "))
print("prefix", sys.prefix)
print("base_prefix", sys.base_prefix)
print("site", site.getsitepackages()[:3])
PY
}

check_imports() {
  local py="$1"
  section "CoCoA imports through venv"
  if [[ ! -x "$py" ]]; then
    mark_fail "cannot import-test with missing venv python"
    return
  fi
  (
    cd "$COCOA_ROOT" || exit 2
    run_bounded "$py" - <<'PY'
mods = [
    "openai",
    "numpy",
    "yaml",
    "requests",
    "PIL",
    "playwright",
    "agent_sandbox",
    "websocket",
    "anthropic",
    "google.genai",
]
failed = False
for mod in mods:
    try:
        __import__(mod)
        print(mod, "ok")
    except Exception as exc:
        failed = True
        print(mod, "FAIL", type(exc).__name__, str(exc)[:160])
raise SystemExit(1 if failed else 0)
PY
  ) || mark_fail "one or more CoCoA imports failed"
}

check_help() {
  local py="$1"
  section "parallel_inference.py help"
  if [[ ! -x "$py" ]]; then
    mark_fail "cannot run help with missing venv python"
    return
  fi
  (
    cd "$COCOA_ROOT" || exit 2
    run_bounded "$py" parallel_inference.py --help | head -60
  ) || mark_fail "parallel_inference.py --help failed"
}

printf 'host=%s\n' "$(hostname 2>/dev/null || true)"
printf 'date=%s\n' "$(date -Iseconds 2>/dev/null || date)"
printf 'cocoa_root=%s\n' "$COCOA_ROOT"

section "Project metadata"
if [[ -d "$COCOA_ROOT" ]]; then
  print_path "$COCOA_ROOT"
  [[ -f "$COCOA_ROOT/.python-version" ]] && sed -n '1,20p' "$COCOA_ROOT/.python-version" || mark_fail "missing .python-version"
  if [[ -f "$COCOA_ROOT/pyproject.toml" ]]; then
    grep -nE 'requires-python|dependencies' "$COCOA_ROOT/pyproject.toml" | head -20 || true
  else
    mark_fail "missing pyproject.toml"
  fi
else
  mark_fail "missing COCOA_ROOT: $COCOA_ROOT"
fi

section "Venv links"
VENV_PY="$COCOA_ROOT/.venv/bin/python"
for path in "$COCOA_ROOT/.venv" "$VENV_PY" "$COCOA_ROOT/.venv/bin/python3" "$COCOA_ROOT/.venv/bin/python3.13" "$COCOA_ROOT/.venv/pyvenv.cfg"; do
  print_path "$path"
done
[[ -f "$COCOA_ROOT/.venv/pyvenv.cfg" ]] && sed -n '1,80p' "$COCOA_ROOT/.venv/pyvenv.cfg"

section "uv state"
print_path "$UV_BIN"
if [[ -x "$UV_BIN" ]]; then
  run_bounded "$UV_BIN" --version || true
  run_bounded "$UV_BIN" cache dir || true
  run_bounded "$UV_BIN" python list --only-installed 2>&1 | head -80 || true
else
  printf 'uv_missing\n'
fi
print_path "$COCOA_EXPECTED_UV_PY_ROOT"
print_path "$COCOA_EXPECTED_UV_PY_ROOT/bin/python3.13"

check_python "shared conda cocoa python" "$COCOA_CONDA_PY"
check_python "cocoa venv python" "$VENV_PY"
check_imports "$VENV_PY"
check_help "$VENV_PY"

section "Summary"
if [[ "$failures" -eq 0 ]]; then
  printf 'cocoabench_env=ok\n'
else
  printf 'cocoabench_env=fail failures=%s\n' "$failures"
fi

exit "$failures"
