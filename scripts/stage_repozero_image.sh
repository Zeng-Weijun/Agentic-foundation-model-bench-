#!/usr/bin/env bash
set -euo pipefail

IMAGE_REF="${IMAGE_REF:-ghcr.io/jessezzzzz/repoarena-new:latest}"
ASSET_ROOT="${ASSET_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench}"
TARGET_DIR="${TARGET_DIR:-$ASSET_ROOT/images/repozero}"
TAR_NAME="${TAR_NAME:-repoarena-new_latest.tar}"
DOCKER_BIN="${DOCKER_BIN:-docker}"
EXECUTE=0
PULL_IMAGE=1

usage() {
  cat <<'EOF'
Usage: scripts/stage_repozero_image.sh [--execute] [--no-pull]

Dry-run-first helper for staging the RepoZero/RepoArena Docker image into the
shared offline image asset root. Run it on dev after GHCR auth is fixed, or on
another internet-enabled Linux staging host with Docker and shared-storage
access. By default this prints checks and target paths without writing image
files or pulling images.

Environment overrides:
  IMAGE_REF    Docker image ref to stage.
  ASSET_ROOT   Shared asset root.
  TARGET_DIR   Final directory for the tar and checksum.
  TAR_NAME     Final tar filename.
  DOCKER_BIN   Container CLI, default docker.

Options:
  --execute    Pull, save, checksum, and write metadata.
  --no-pull    Skip docker pull and save the currently local IMAGE_REF.
  -h, --help   Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute)
      EXECUTE=1
      ;;
    --no-pull)
      PULL_IMAGE=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

TAR_PATH="$TARGET_DIR/$TAR_NAME"
SHA_PATH="$TAR_PATH.sha256"
INSPECT_PATH="$TARGET_DIR/${TAR_NAME%.tar}.docker-inspect.json"
MANIFEST_PATH="$TARGET_DIR/${TAR_NAME%.tar}.manifest.json"

require_tool() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required tool: $1" >&2
    exit 127
  fi
}

print_plan() {
  cat <<EOF
RepoZero image staging plan
  image:       $IMAGE_REF
  target_dir:  $TARGET_DIR
  tar:         $TAR_PATH
  sha256:      $SHA_PATH
  inspect:     $INSPECT_PATH
  manifest:    $MANIFEST_PATH
  docker_bin:  $DOCKER_BIN
  mode:        $([[ "$EXECUTE" -eq 1 ]] && echo execute || echo dry-run)
EOF
}

require_tool "$DOCKER_BIN"
require_tool sha256sum
print_plan

"$DOCKER_BIN" info >/dev/null

if [[ "$EXECUTE" -ne 1 ]]; then
  cat <<EOF

Dry run only. To stage on an internet-enabled host with GHCR access:
  docker login ghcr.io
  IMAGE_REF='$IMAGE_REF' ASSET_ROOT='$ASSET_ROOT' \\
    bash scripts/stage_repozero_image.sh --execute

Expected staged files:
  $TAR_PATH
  $SHA_PATH
  $INSPECT_PATH
  $MANIFEST_PATH

This script never contacts or mutates the worker. Load on worker later with:
  DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker load -i '$TAR_PATH'
EOF
  exit 0
fi

mkdir -p "$TARGET_DIR"

if [[ "$PULL_IMAGE" -eq 1 ]]; then
  "$DOCKER_BIN" pull "$IMAGE_REF"
fi

"$DOCKER_BIN" image inspect "$IMAGE_REF" > "$INSPECT_PATH.tmp"
mv "$INSPECT_PATH.tmp" "$INSPECT_PATH"

if "$DOCKER_BIN" manifest inspect "$IMAGE_REF" > "$MANIFEST_PATH.tmp" 2>"$MANIFEST_PATH.err"; then
  mv "$MANIFEST_PATH.tmp" "$MANIFEST_PATH"
  rm -f "$MANIFEST_PATH.err"
else
  rm -f "$MANIFEST_PATH.tmp"
  echo "warning: docker manifest inspect failed; see $MANIFEST_PATH.err" >&2
fi

tmp_tar="$TAR_PATH.tmp.$$"
rm -f "$tmp_tar"
"$DOCKER_BIN" save -o "$tmp_tar" "$IMAGE_REF"
mv "$tmp_tar" "$TAR_PATH"

(
  cd "$TARGET_DIR"
  sha256sum "$TAR_NAME" > "$(basename "$SHA_PATH")"
)

cat <<EOF
Staged RepoZero image tar:
  $TAR_PATH
  $SHA_PATH
EOF
