# Terminal-Bench 2.1 Fix-Git Rebuild Execution

Date: 2026-06-25

Scope: surface:51 Terminal-Bench 2.1 image lane. This run used local tmux as
the control-plane persistence wrapper and `ssh dev` for remote execution. No
worker benchmark/model run was launched. No commit or push was performed.

## Inputs Read

- `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`
- `reports/terminal_bench_fix_git_rebuild_plan_20260625.md`
- `scripts/rebuild_tb21_fix_git_image.sh`

## Safety Assessment

The rebuild script is dry-run-first and only executes writes under `--execute`.
Its real execution writes to the shared Terminal-Bench image output directory:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild
```

It does not edit the upstream Terminal-Bench task, this repo, or the original
`20260425/fix-git.tar`. It generates a temporary BuildKit Dockerfile that uses
bind mounts for `setup.sh` and `resources/`, then saves/checksums the resulting
image if the build succeeds.

I treated the script as safe to execute on `dev` under a local tmux wrapper.

## Execution Command

Local tmux session:

```text
tb21_fixgit_rebuild_20260625_223806_s51
```

Readable command shape:

```bash
cd /Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-
tmux new-session -d -s tb21_fixgit_rebuild_20260625_223806_s51 \
  "cd /Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench- &&
   ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<remote wrapper>' \
     < scripts/rebuild_tb21_fix_git_image.sh"
```

Remote wrapper behavior:

```bash
source ~/.bashrc >/dev/null 2>&1 || true
export TMPDIR=/data/tmp
mkdir -p /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs
bash -s -- --execute > "$LOG" 2>&1
echo "$rc" > "$LOG.rc"
```

The first tmux launch attempt failed before remote execution because the local
shell expanded remote `$LOG/$RC/$rc` while constructing the command. That
attempt produced no remote log and did not start Docker. I then verified the
corrected remote-wrapper quoting with a foreground `--dry-run` probe:

```text
log=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/tb21_fix_git_rebuild_wrapper_probe_surface51.log
rc=0
```

## Real Rebuild Log

```text
log=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/tb21_fix_git_rebuild_20260625_223806_surface51.log
rc_file=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/tb21_fix_git_rebuild_20260625_223806_surface51.log.rc
rc=1
remote_host=zwj2
start_time=2026-06-25T22:38:07+08:00
end_time=2026-06-25T22:38:29+08:00
```

Failure tail:

```text
#3 DONE 6.9s
ERROR: failed to build: failed to receive status: rpc error: code = Unavailable desc = error reading from server: EOF
end_time=2026-06-25T22:38:29+08:00
exit_code=1
```

The build reached BuildKit frontend image resolution/extraction:

```text
docker-image://docker.io/docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
```

It failed before building the task layers and before `docker save`.

## Artifact Status

Target directory:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild
```

Observed status after failure:

```text
tar: missing
checksum: missing
docker-inspect JSON: missing
layer-scan: missing
manifest: not produced by this script; no replacement image manifest was written
```

The target directory exists, but the post-failure `find "$DEST" -maxdepth 1
-type f` check printed no files.

## Blocker

The real blocker is the `dev` Docker daemon/buildx state during the build, not
missing `fix-git` source files.

Immediately after the build failure:

```text
docker_ps_rc=1
Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?
docker.service Active: failed (Result: exit-code) since Thu 2026-06-25 22:38:29 HKT
```

`journalctl -u docker` shows the daemon panic and failed restarts:

```text
Jun 25 22:38:18 zwj2 dockerd[...] panic: misplaced bucket header: ...
Jun 25 22:38:18 zwj2 dockerd[...] github.com/moby/buildkit/solver/bboltcachestorage.(*Store).AddResult
Jun 25 22:38:18 zwj2 systemd[1]: docker.service: Main process exited, code=exited, status=2/INVALIDARGUMENT
```

Then Docker restart attempts failed on a bridge-network conflict:

```text
failed to start daemon: Error initializing network controller:
error creating default "bridge" network ... (docker0):
conflicts with network ... (docker0): networks have same bridge name
```

I did not restart Docker or mutate Docker network state because that could
disrupt other concurrent work on `dev`.

## Commands And Exit Codes

```text
sed -n '1,1040p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md >/tmp/codex_workflow_surface51_read.txt && cd .../Agentic-foundation-model-bench- && pwd
rc=0

sed -n '1,280p' reports/terminal_bench_fix_git_rebuild_plan_20260625.md
rc=0

sed -n '1,320p' scripts/rebuild_tb21_fix_git_image.sh
rc=0

foreground remote-wrapper --dry-run probe via ssh dev
rc=0

tmux new-session -d -s tb21_fixgit_rebuild_20260625_223806_s51 '<ssh dev real --execute wrapper>'
rc=0

remote rebuild script, captured in rc_file
rc=1

tmux list-sessions | rg tb21_fixgit_rebuild_20260625_223806_s51 || true
rc=0, no matching live session after failure

ssh dev '<docker ps/systemctl status/process read-only diagnostics>'
rc=0; docker_ps_rc=1; docker.service failed

ssh dev 'journalctl -u docker --no-pager -n 120'
rc=0
```

## Next Safe Step

Do not rerun this build on `dev` until Docker is intentionally recovered. A
safe recovery should be coordinated because the daemon is failed after a
BuildKit/bbolt panic and restart is blocked by a stale/duplicate `docker0`
network state. After recovery, rerun the same script command; if it produces
the tar/checksum/layer-scan, then load the rebuilt tar on the worker rootless
daemon as described in the rebuild plan.
