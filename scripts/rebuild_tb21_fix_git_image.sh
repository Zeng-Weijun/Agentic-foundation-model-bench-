#!/usr/bin/env bash
set -euo pipefail

TASK_ENV_DIR="${TASK_ENV_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks/fix-git/environment}"
IMAGE_TAG="${IMAGE_TAG:-tb2-offline/fix-git:20260425}"
DEST_DIR="${DEST_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild}"
TAR_NAME="${TAR_NAME:-fix-git.tar}"
WORK_ROOT="${WORK_ROOT:-${TMPDIR:-/data/tmp}/tb21-fix-git-rebuild}"
DOCKER_BIN="${DOCKER_BIN:-docker}"
EXECUTE=0
NO_CACHE=0

usage() {
  cat <<'EOF'
Usage: scripts/rebuild_tb21_fix_git_image.sh [--dry-run|--execute] [--no-cache]

Dry-run-first helper for rebuilding the Terminal-Bench 2.1 fix-git image on
the internet-enabled dev host. The generated Dockerfile uses BuildKit bind
mounts for setup.sh and resources, so /app/resources/patch_files is not created
in one persisted layer and removed in a later layer.

Defaults:
  source: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks/fix-git/environment
  tag:    tb2-offline/fix-git:20260425
  output: /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild/fix-git.tar

Environment overrides:
  TASK_ENV_DIR  Directory containing Dockerfile, setup.sh, and resources/.
  IMAGE_TAG     Image tag to build and save.
  DEST_DIR      Durable shared output directory for tar/checksum/metadata.
  TAR_NAME      Output tar filename.
  WORK_ROOT     Temporary build context root, default uses TMPDIR or /data/tmp.
  DOCKER_BIN    Container CLI, default docker.

Options:
  --dry-run     Print the plan only. This is the default.
  --execute     Actually build, save, checksum, and scan the tar.
  --no-cache    Pass --no-cache to docker buildx build.
  -h, --help    Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      EXECUTE=0
      ;;
    --execute)
      EXECUTE=1
      ;;
    --no-cache)
      NO_CACHE=1
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

TAR_PATH="$DEST_DIR/$TAR_NAME"
SHA_PATH="$TAR_PATH.sha256"
INSPECT_PATH="$DEST_DIR/${TAR_NAME%.tar}.docker-inspect.json"
LAYER_SCAN_PATH="$DEST_DIR/${TAR_NAME%.tar}.layer-scan.txt"

require_tool() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required tool: $1" >&2
    exit 127
  fi
}

print_plan() {
  cat <<EOF
Terminal-Bench 2.1 fix-git rebuild plan
  source_env:  $TASK_ENV_DIR
  image_tag:   $IMAGE_TAG
  dest_dir:    $DEST_DIR
  tar:         $TAR_PATH
  sha256:      $SHA_PATH
  inspect:     $INSPECT_PATH
  layer_scan:  $LAYER_SCAN_PATH
  work_root:   $WORK_ROOT
  docker_bin:  $DOCKER_BIN
  mode:        $([[ "$EXECUTE" -eq 1 ]] && echo execute || echo dry-run)
EOF
}

print_generated_dockerfile() {
  cat <<'EOF'

Generated Dockerfile template:
  # syntax=docker/dockerfile:1.7
  FROM python:3.13-slim-bookworm

  WORKDIR /app

  RUN apt-get update && apt-get install -y git

  RUN --mount=type=bind,source=setup.bind.sh,target=/tmp/setup.sh,readonly \
      --mount=type=bind,source=resources,target=/tmp/tb21_resources,readonly \
      bash /tmp/setup.sh

  WORKDIR /app/personal-site
EOF
}

write_context() {
  local context_dir="$1"
  mkdir -p "$context_dir"
  cp -a "$TASK_ENV_DIR/resources" "$context_dir/resources"
  sed 's#/app/resources#/tmp/tb21_resources#g' \
    "$TASK_ENV_DIR/setup.sh" > "$context_dir/setup.bind.sh"
  cat > "$context_dir/Dockerfile" <<'EOF'
# syntax=docker/dockerfile:1.7
FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y git

RUN --mount=type=bind,source=setup.bind.sh,target=/tmp/setup.sh,readonly \
    --mount=type=bind,source=resources,target=/tmp/tb21_resources,readonly \
    bash /tmp/setup.sh

WORKDIR /app/personal-site
EOF
}

scan_saved_tar() {
  local tar_path="$1"
  local scan_path="$2"
  python3 - "$tar_path" "$scan_path" <<'PY'
import io
import sys
import tarfile

image_tar, scan_path = sys.argv[1:3]
matches = []

with tarfile.open(image_tar, "r:*") as outer:
    for member in outer.getmembers():
        if not member.isfile():
            continue
        extracted = outer.extractfile(member)
        if extracted is None:
            continue
        data = extracted.read()
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as inner:
                for nested in inner.getnames():
                    if (
                        "app/resources/patch_files" in nested
                        or "app/resources/.wh.patch_files" in nested
                        or "app/.wh.resources" in nested
                    ):
                        matches.append(f"{member.name}: {nested}")
        except tarfile.TarError:
            continue

with open(scan_path, "w", encoding="utf-8") as fh:
    if matches:
        fh.write("unexpected app/resources markers found\n")
        for match in matches:
            fh.write(match + "\n")
    else:
        fh.write("no app/resources/patch_files layer entries found\n")

if matches:
    raise SystemExit(1)
PY
}

print_plan
print_generated_dockerfile

if [[ "$EXECUTE" -ne 1 ]]; then
  cat <<EOF

Dry run only. To rebuild on dev after confirming the source paths:
  bash scripts/rebuild_tb21_fix_git_image.sh --execute

The resulting worker load check is:
  DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker load -i '$TAR_PATH'
  DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker image inspect '$IMAGE_TAG'
EOF
  exit 0
fi

require_tool "$DOCKER_BIN"
require_tool sha256sum
require_tool sed
require_tool python3

[[ -f "$TASK_ENV_DIR/Dockerfile" ]] || { echo "missing source Dockerfile: $TASK_ENV_DIR/Dockerfile" >&2; exit 2; }
[[ -f "$TASK_ENV_DIR/setup.sh" ]] || { echo "missing source setup.sh: $TASK_ENV_DIR/setup.sh" >&2; exit 2; }
[[ -d "$TASK_ENV_DIR/resources/patch_files" ]] || { echo "missing source resources/patch_files under $TASK_ENV_DIR" >&2; exit 2; }

"$DOCKER_BIN" info >/dev/null

mkdir -p "$WORK_ROOT" "$DEST_DIR"
context_dir="$(mktemp -d "$WORK_ROOT/context.XXXXXX")"
tmp_tar="$TAR_PATH.tmp.$$"
trap 'rm -rf "$context_dir"; rm -f "$tmp_tar"' EXIT

write_context "$context_dir"

build_args=(buildx build --progress=plain --load -t "$IMAGE_TAG" -f "$context_dir/Dockerfile")
if [[ "$NO_CACHE" -eq 1 ]]; then
  build_args+=(--no-cache)
fi
build_args+=("$context_dir")

DOCKER_BUILDKIT=1 "$DOCKER_BIN" "${build_args[@]}"

"$DOCKER_BIN" image inspect "$IMAGE_TAG" > "$INSPECT_PATH.tmp"
mv "$INSPECT_PATH.tmp" "$INSPECT_PATH"

rm -f "$tmp_tar"
"$DOCKER_BIN" save -o "$tmp_tar" "$IMAGE_TAG"
mv "$tmp_tar" "$TAR_PATH"

(
  cd "$DEST_DIR"
  sha256sum "$TAR_NAME" > "$(basename "$SHA_PATH")"
)

scan_saved_tar "$TAR_PATH" "$LAYER_SCAN_PATH"

cat <<EOF
Rebuilt Terminal-Bench fix-git image tar:
  $TAR_PATH
  $SHA_PATH
  $INSPECT_PATH
  $LAYER_SCAN_PATH

Load on worker with:
  DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker load -i '$TAR_PATH'
  DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker image inspect '$IMAGE_TAG'
EOF
