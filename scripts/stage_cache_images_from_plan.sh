#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: stage_cache_images_from_plan.sh --plan PLAN.tsv [--execute] [--push] [--source-host-label HOST] [--output-tsv OUT.tsv] [--only ID_OR_SLUG] [--save-timeout-seconds SECONDS]

Dry-run by default. With --execute, docker-save matched rows from PLAN.tsv to
fallback_tar. Use --save-timeout-seconds to bound docker save on large or stuck images. With --push, also docker tag/push p0_tag after saving. The script
must run on the source Docker host named by the staging plan, for example
swe_dev for Terminal-Bench cache rows.
EOF
}

PLAN=""
EXECUTE=0
PUSH=0
OUTPUT_TSV=""
SOURCE_HOST_LABEL=""
ONLY_VALUES=()
SAVE_TIMEOUT_SECONDS=0

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
    --source-host-label)
      SOURCE_HOST_LABEL="$2"
      shift 2
      ;;
    --only)
      ONLY_VALUES+=("$2")
      shift 2
      ;;
    --save-timeout-seconds)
      SAVE_TIMEOUT_SECONDS="$2"
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
case "$SAVE_TIMEOUT_SECONDS" in
  ''|*[!0-9]*)
    echo "--save-timeout-seconds must be a non-negative integer" >&2
    exit 2
    ;;
esac

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

inspect_image_id() {
  local ref="$1"
  docker image inspect "$ref" | python3 -c 'import json, sys; payload=json.load(sys.stdin); doc=payload[0] if isinstance(payload, list) and payload else payload; print(doc.get("Id", "") if isinstance(doc, dict) else "")'
}

write_result_row() {
  local row_status="$1"
  if [ -z "$OUTPUT_TSV" ]; then
    return 0
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$id" "$slug" "$local_ref" "$source_image_id" "$source_host" "$source_ref" "$source_cache_image_id" "$source_size" \
    "$fallback_tar" "$fallback_sha" "$p0_tag" "$p0_digest_ref" "$actual_image_id" "$row_status" >> "$OUTPUT_TSV"
}

if [ -n "$OUTPUT_TSV" ]; then
  mkdir -p "$(dirname "$OUTPUT_TSV")"
  printf 'id\tslug\tlocal_ref\tsource_image_id\tsource_host\tsource_ref\tsource_cache_image_id\tsource_size\tfallback_tar\tfallback_tar_sha256\tp0_tag\tp0_digest_ref\tactual_image_id\tstatus\n' > "$OUTPUT_TSV"
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
  actual_image_id=""
  status="dry_run"

  if [ -n "$SOURCE_HOST_LABEL" ] && [ -n "$source_host" ] && [ "$source_host" != "$SOURCE_HOST_LABEL" ]; then
    echo "FAIL source host mismatch $id expected_source_host=$source_host current_source_host=$SOURCE_HOST_LABEL" >&2
    failed=$((failed + 1))
    status="source_host_mismatch"
    write_result_row "$status"
    continue
  fi

  if [ "$EXECUTE" -eq 1 ]; then
    actual_image_id="$(inspect_image_id "$local_ref")"
    if [ -n "$source_image_id" ] && [ "$actual_image_id" != "$source_image_id" ]; then
      echo "FAIL image identity mismatch $id expected=$source_image_id actual=$actual_image_id" >&2
      failed=$((failed + 1))
      status="identity_mismatch"
      write_result_row "$status"
      continue
    fi
    mkdir -p "$(dirname "$fallback_tar")"
    tmp_tar="${fallback_tar}.tmp.$$"
    rm -f "$tmp_tar"
    if [ "$SAVE_TIMEOUT_SECONDS" -gt 0 ]; then
      set +e
      timeout "$SAVE_TIMEOUT_SECONDS" docker save -o "$tmp_tar" "$local_ref"
      save_rc=$?
      set -e
    else
      set +e
      docker save -o "$tmp_tar" "$local_ref"
      save_rc=$?
      set -e
    fi
    if [ "$save_rc" -ne 0 ]; then
      rm -f "$tmp_tar"
      if [ "$SAVE_TIMEOUT_SECONDS" -gt 0 ] && [ "$save_rc" -eq 124 ]; then
        echo "FAIL docker save timeout $id after ${SAVE_TIMEOUT_SECONDS}s" >&2
        status="save_timeout"
      else
        echo "FAIL docker save failed $id rc=$save_rc" >&2
        status="save_failed"
      fi
      failed=$((failed + 1))
      write_result_row "$status"
      continue
    fi
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
      if [ -z "$p0_digest_ref" ]; then
        echo "FAIL missing p0 digest after push $id p0_tag=$p0_tag" >&2
        failed=$((failed + 1))
        status="push_digest_missing"
        write_result_row "$status"
        continue
      fi
      status="saved_pushed"
    fi
    staged=$((staged + 1))
  fi

  write_result_row "$status"
done < "$PLAN"

if [ "$failed" -gt 0 ]; then
  echo "stage_cache_images_from_plan: rows=$count staged=$staged skipped=$skipped failed=$failed" >&2
  exit 1
fi

echo "stage_cache_images_from_plan: rows=$count staged=$staged skipped=$skipped failed=$failed"
