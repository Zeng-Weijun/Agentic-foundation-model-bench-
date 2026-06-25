#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"

DEFAULT_MANIFEST="$REPO_ROOT/manifests/offline_images.example.yaml"
DEFAULT_ASSET_ROOT="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench"
DEFAULT_DOCKER_HOST="unix:///tmp/rl/run/docker.sock"

has_mode=0
for arg in "$@"; do
  case "$arg" in
    --check|--dry-run|--load)
      has_mode=1
      ;;
  esac
done

args=(
  "--manifest" "$DEFAULT_MANIFEST"
  "--asset-root" "$DEFAULT_ASSET_ROOT"
  "--docker-host" "${DOCKER_HOST:-$DEFAULT_DOCKER_HOST}"
)

if [[ "$has_mode" -eq 0 ]]; then
  args+=("--load")
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/check_offline_images_manifest.py" "${args[@]}" "$@"
