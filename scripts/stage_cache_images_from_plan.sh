#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: stage_cache_images_from_plan.sh --plan PLAN.tsv [--execute] [--push] [--output-tsv OUT.tsv] [--only ID_OR_SLUG]

Dry-run by default. With --execute, docker-save matched rows from PLAN.tsv to
fallback_tar. With --push, also docker tag/push p0_tag after saving. The script
must run on the source Docker host named by the staging plan, for example
swe_dev for Terminal-Bench cache rows.
EOF
}

PLAN=""
EXECUTE=0
PUSH=0
OUTPUT_TSV=""
ONLY_VALUES=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    --plan)
      PLAN="$2"
      shift 2
      ;;
    --execute)
      EXECUTE=1
      shift
      ;;
    --push)
      PUSH=1
      shift
      ;;
    --output-tsv)
      OUTPUT_TSV="$2"
      shift 2
      ;;
    --only)
      ONLY_VALUES+=("$2")
      shift 2
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
done

if [ -z "$PLAN" ]; then
  echo "--plan is required" >&2
  usage >&2
  exit 2
fi
if [ ! -f "$PLAN" ]; then
  echo "plan TSV not found: $PLAN" >&2
  exit 2
fi
if [ "$PUSH" -eq 1 ] && [ "$EXECUTE" -ne 1 ]; then
  echo "--push requires --execute" >&2
  exit 2
fi

selected() {
  local id="$1"
  local slug="$2"
  if [ "${#ONLY_VALUES[@]}" -eq 0 ]; then
    return 0
  fi
  local value
  for value in "${ONLY_VALUES[@]}"; do
    if [ "$value" = "$id" ] || [ "$value" = "$slug" ]; then
      return 0
    fi
  done
  return 1
}

if [ -n "$OUTPUT_TSV" ]; then
  mkdir -p "$(dirname "$OUTPUT_TSV")"
  printf 'id\tslug\tlocal_ref\tsource_image_id\tfallback_tar\tfallback_tar_sha256\tp0_tag\tp0_digest_ref\tstatus\n' > "$OUTPUT_TSV"
fi

count=0
staged=0
skipped=0
failed=0

while IFS=$'\t' read -r id slug local_ref source_image_id source_host source_ref source_cache_image_id source_size fallback_tar p0_tag match_status rest; do
  if [ "$id" = "id" ]; then
    continue
  fi
  if ! selected "$id" "$slug"; then
    skipped=$((skipped + 1))
    continue
  fi
  count=$((count + 1))
  if [ "$match_status" != "matched" ]; then
    echo "SKIP unmatched $id $match_status" >&2
    skipped=$((skipped + 1))
    continue
  fi
  if [ -z "$local_ref" ] || [ -z "$fallback_tar" ]; then
    echo "FAIL malformed row $id" >&2
    failed=$((failed + 1))
    continue
  fi

  echo "ROW $id local_ref=$local_ref fallback_tar=$fallback_tar p0_tag=$p0_tag"
  fallback_sha=""
  p0_digest_ref=""
  status="dry_run"

  if [ "$EXECUTE" -eq 1 ]; then
    docker image inspect "$local_ref" >/dev/null
    mkdir -p "$(dirname "$fallback_tar")"
    tmp_tar="${fallback_tar}.tmp.$$"
    rm -f "$tmp_tar"
    docker save -o "$tmp_tar" "$local_ref"
    mv "$tmp_tar" "$fallback_tar"
    chmod 0644 "$fallback_tar"
    fallback_sha="$(sha256sum "$fallback_tar" | awk '{print $1}')"
    status="saved"
    if [ "$PUSH" -eq 1 ]; then
      if [ -z "$p0_tag" ]; then
        echo "FAIL missing p0_tag for $id" >&2
        failed=$((failed + 1))
        continue
      fi
      docker tag "$local_ref" "$p0_tag"
      docker push "$p0_tag"
      p0_digest_ref="$(docker inspect --format='{{index .RepoDigests 0}}' "$p0_tag" 2>/dev/null || true)"
      status="saved_pushed"
    fi
    staged=$((staged + 1))
  fi

  if [ -n "$OUTPUT_TSV" ]; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$id" "$slug" "$local_ref" "$source_image_id" "$fallback_tar" "$fallback_sha" "$p0_tag" "$p0_digest_ref" "$status" >> "$OUTPUT_TSV"
  fi
done < "$PLAN"

if [ "$failed" -gt 0 ]; then
  echo "stage_cache_images_from_plan: rows=$count staged=$staged skipped=$skipped failed=$failed" >&2
  exit 1
fi

echo "stage_cache_images_from_plan: rows=$count staged=$staged skipped=$skipped failed=$failed"
