import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "agentic_bench_suite.py"


def load_module():
    spec = importlib.util.spec_from_file_location("agentic_bench_suite", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SUITE_YAML = textwrap.dedent(
    """
    schema_version: agentic_bench.suite.v1
    suite:
      id: unit_smoke
      mode: smoke
      controller_host: dev
      run_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs
      concurrency: 2
      default_worker_host: worker
      offline_policy:
        network_policy: offline_or_internal_only
        forbid_public_internet: true
        rootless_required: true
    model_profiles:
      - id: gpt54mini_8130
        model_name: gpt-5.4-mini
        provider: openai_compatible_relay
        base_url: http://8.130.49.170/v1
        api_key_env: OPENAI_API_KEY
        api_key_policy: env_only
        max_tokens: "4096"
      - id: qwen_sglang_future
        model_name: Qwen/Qwen3-Coder-Future
        provider: sglang
        base_url_env: SGLANG_OPENAI_BASE_URL
        api_key_policy: empty_allowed
    benches:
      - id: tau3_bench_smoke
        benchmark: tau3-bench
        adapter: tau3_bench
        adapter_script: run_tau3_bench.sh
        adapter_status: pending_adapter
        model_profile: gpt54mini_8130
        worker_host: worker
        concurrency: 1
        params:
          TAU3_LIMIT: 1
          TAU3_DOMAINS: airline
    """
).strip()


WORKER_STYLE_YAML = textwrap.dedent(
    """
    schema_version: agentic_bench.suite.v1
    suite:
      id_prefix: worker_gpt54mini_smoke
      mode: smoke
      dry_run_default: true
      concurrency: 2
      controller_host: dev
      output_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs
    execution:
      kind: ssh_worker
    worker:
      id: worker-j9jjd
      host: worker
      rootless: null
      tmp_root: /data/tmp/agentic-foundation-model-bench
      network_policy: offline_or_internal_only
      offline: true
    active_model: relay_gpt54mini_8130
    model_profiles:
      relay_gpt54mini_8130:
        MODEL_NAME: gpt-5.4-mini
        LITELLM_MODEL: openai/gpt-5.4-mini
        OPENAI_BASE_URL: http://8.130.49.170/v1
        OPENAI_API_KEY: env:OPENAI_API_KEY
      qwen3_coder_30b_a3b_sglang_template:
        MODEL_NAME: Qwen/Qwen3-Coder-30B-A3B-Instruct
        OPENAI_BASE_URL: http://100.103.11.77:8503/v1
        OPENAI_API_KEY: EMPTY
      dev_proxy_gpt54mini_8130:
        MODEL_NAME: gpt-5.4-mini
        OPENAI_BASE_URL: http://100.96.1.101:18540/v1
        OPENAI_API_KEY: env:OPENAI_API_KEY
        BENCH_MODEL_PROFILE: gpt54mini_8130
    benchmarks:
      - id: repozero_py2js
        script: run_repozero_py2js.sh
        adapter_status: existing_legacy
        modes: [smoke, full]
        env_by_mode:
          smoke:
            REPOZERO_MODE: smoke
    """
).strip()


class RootlessWorkerHealthScriptTest(unittest.TestCase):
    def test_health_script_reports_storage_and_optional_cached_run_smoke(self):
        script = (ROOT / "scripts" / "check_rootless_docker_worker.sh").read_text(encoding="utf-8")
        self.assertIn("HEALTH_SMOKE_IMAGE", script)
        self.assertIn("--- docker storage ---", script)
        self.assertIn("docker system df", script)
        self.assertIn("--- cached run smoke ---", script)

    def test_health_script_exports_worker_docker_api_version(self):
        script = (ROOT / "scripts" / "check_rootless_docker_worker.sh").read_text(encoding="utf-8")
        self.assertIn("REMOTE_DOCKER_API_VERSION", script)
        self.assertIn("export DOCKER_API_VERSION=", script)
        self.assertIn("docker_api_version=$DOCKER_API_VERSION", script)

    def test_health_script_treats_version_endpoint_as_diagnostic(self):
        script = (ROOT / "scripts" / "check_rootless_docker_worker.sh").read_text(encoding="utf-8")
        docker_version_section = script.split("echo \"--- docker version ---\"", 1)[1].split(
            "echo \"--- raw version endpoint ---\"", 1
        )[0]
        raw_version_section = script.split("echo \"--- raw version endpoint ---\"", 1)[1].split(
            "echo \"--- docker ps ---\"", 1
        )[0]
        sdk_version_section = script.split("echo \"--- python docker sdk version ---\"", 1)[1].split(
            "echo \"--- non-host rootless network prerequisites ---\"", 1
        )[0]
        self.assertIn("known_rootless_version_endpoint_unstable", script)
        self.assertNotIn("status=1", docker_version_section)
        self.assertNotIn("status=1", raw_version_section)
        self.assertNotIn("status=1", sdk_version_section)


class AgenticBenchSuiteTest(unittest.TestCase):
    def test_default_plan_is_dry_run_and_secret_safe(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "suite.yaml"
            suite_path.write_text(SUITE_YAML, encoding="utf-8")
            old_key = os.environ.get("OPENAI_API_KEY")
            os.environ["OPENAI_API_KEY"] = "sk-should-never-appear"
            try:
                config = module.load_suite_config(suite_path)
                plan = module.build_run_plan(config, suite_path=suite_path, dry_run=True, smoke=False)
            finally:
                if old_key is None:
                    os.environ.pop("OPENAI_API_KEY", None)
                else:
                    os.environ["OPENAI_API_KEY"] = old_key

        rendered = json.dumps(plan, sort_keys=True)
        self.assertEqual(plan["suite_id"], "unit_smoke")
        self.assertTrue(plan["dry_run"])
        self.assertEqual(plan["controller_host"], "dev")
        self.assertEqual(plan["suite_concurrency"], 2)
        self.assertEqual(plan["runs"][0]["worker_host"], "worker")
        self.assertEqual(plan["runs"][0]["network_policy"], "offline_or_internal_only")
        self.assertTrue(plan["runs"][0]["rootless_required"])
        self.assertTrue(plan["runs"][0]["model"]["api_key_set"])
        self.assertIn("OPENAI_API_KEY", rendered)
        self.assertNotIn("sk-should-never-appear", rendered)
        self.assertIn("DRY_RUN=1", plan["runs"][0]["command_preview"])
        self.assertIn("MAX_TOKENS=4096", plan["runs"][0]["command_preview"])

    def test_plan_emits_proxy_concurrency_ceiling(self):
        module = load_module()
        suite_text = SUITE_YAML.replace("  concurrency: 2\n", "  concurrency: 2\n  proxy_concurrency_ceiling: 2\n", 1)
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "suite.yaml"
            suite_path.write_text(suite_text, encoding="utf-8")
            config = module.load_suite_config(suite_path)
            plan = module.build_run_plan(config, suite_path=suite_path, dry_run=True, smoke=False)

        self.assertEqual(plan["suite_concurrency"], 2)
        self.assertEqual(plan["proxy_concurrency_ceiling"], 2)

    def test_cli_rejects_max_concurrency_above_proxy_ceiling(self):
        suite_text = SUITE_YAML.replace("  concurrency: 2\n", "  concurrency: 2\n  proxy_concurrency_ceiling: 2\n", 1)
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "suite.yaml"
            suite_path.write_text(suite_text, encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    str(suite_path),
                    "--dry-run",
                    "--json",
                    "--max-concurrency",
                    "3",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("proxy_concurrency_ceiling", proc.stderr)
        self.assertIn("3", proc.stderr)

    def test_cli_readiness_rejects_max_concurrency_above_proxy_ceiling(self):
        suite_text = SUITE_YAML.replace("  concurrency: 2\n", "  concurrency: 2\n  proxy_concurrency_ceiling: 2\n", 1)
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "suite.yaml"
            suite_path.write_text(suite_text, encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    str(suite_path),
                    "--readiness",
                    "--json",
                    "--target-benches",
                    "tau3-bench",
                    "--max-concurrency",
                    "3",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        self.assertIn("proxy_concurrency_ceiling", proc.stderr)
        self.assertIn("3", proc.stderr)

    def test_rejects_swe_dev_controller_for_this_repo_contract(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "suite.yaml"
            suite_path.write_text(SUITE_YAML.replace("controller_host: dev", "controller_host: swe_dev"), encoding="utf-8")
            with self.assertRaisesRegex(module.ConfigError, "controller_host.*dev"):
                module.load_suite_config(suite_path)

    def test_cli_emits_json_plan_without_running_adapter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "suite.yaml"
            suite_path.write_text(SUITE_YAML, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(MODULE_PATH), str(suite_path), "--dry-run", "--json"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        plan = json.loads(proc.stdout)
        self.assertEqual(plan["runs"][0]["status"], "planned")
        self.assertEqual(plan["runs"][0]["adapter_status"], "pending_adapter")
        self.assertIn("not wired", plan["runs"][0]["notes"][0])

    def test_cli_supports_worker_style_suite_with_filters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "worker_suite.yaml"
            suite_path.write_text(WORKER_STYLE_YAML, encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    str(suite_path),
                    "--dry-run",
                    "--json",
                    "--only",
                    "repozero_py2js",
                    "--model-profile",
                    "relay_gpt54mini_8130",
                    "--max-concurrency",
                    "1",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        plan = json.loads(proc.stdout)
        self.assertEqual(plan["suite_id"], "worker_gpt54mini_smoke")
        self.assertEqual(plan["suite_concurrency"], 1)
        self.assertEqual(len(plan["runs"]), 1)
        self.assertEqual(plan["runs"][0]["bench_id"], "repozero_py2js")
        self.assertEqual(plan["runs"][0]["worker_host"], "worker")
        self.assertEqual(plan["runs"][0]["model"]["profile_id"], "relay_gpt54mini_8130")
        self.assertEqual(plan["runs"][0]["params"]["REPOZERO_MODE"], "smoke")
        self.assertIn("bash -c ", plan["runs"][0]["command"])
        self.assertNotIn("bash -lc ", plan["runs"][0]["command"])
        self.assertIn("OPENAI_API_KEY", json.dumps(plan, sort_keys=True))

    def test_model_profile_can_override_legacy_bench_profile_name(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "worker_suite.yaml"
            suite_path.write_text(WORKER_STYLE_YAML, encoding="utf-8")
            config = module.load_suite_config(suite_path)
            plan = module.build_run_plan(
                config,
                suite_path=suite_path,
                dry_run=True,
                model_profile_override="dev_proxy_gpt54mini_8130",
                only={"repozero_py2js"},
            )
        run = plan["runs"][0]
        self.assertEqual(run["model"]["profile_id"], "dev_proxy_gpt54mini_8130")
        self.assertEqual(run["runtime_env"]["BENCH_MODEL_PROFILE"], "gpt54mini_8130")
        self.assertEqual(run["runtime_env"]["OPENAI_BASE_URL"], "http://100.96.1.101:18540/v1")

    def test_image_manifest_adds_explicit_preflight_command_to_run_plan(self):
        module = load_module()
        suite_yaml = SUITE_YAML + textwrap.dedent(
            """

            image_preflight:
              project_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo
              asset_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
              default_policy: required
            worker:
              docker_host: unix:///tmp/rl/run/docker.sock
            """
        )
        suite_yaml = suite_yaml.replace(
            "    concurrency: 1\n    params:",
            "    image_manifest: manifests/images/repozero.yaml\n"
            "    concurrency: 1\n    params:",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "suite.yaml"
            suite_path.write_text(suite_yaml, encoding="utf-8")
            config = module.load_suite_config(suite_path)
            plan = module.build_run_plan(config, suite_path=suite_path, dry_run=True)

        run = plan["runs"][0]
        self.assertEqual(run["image_preflight"]["policy"], "required")
        self.assertTrue(run["image_preflight"]["required"])
        self.assertEqual(run["image_preflight"]["manifest"], "manifests/images/repozero.yaml")
        self.assertIn("scripts/agentic_bench_images.py", run["image_preflight"]["command"])
        self.assertIn("--docker-host unix:///tmp/rl/run/docker.sock", run["image_preflight"]["command"])
        self.assertIn("--asset-root /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench", run["image_preflight"]["command"])
        self.assertIn("image preflight required before adapter execution", run["notes"])

    def test_image_preflight_remote_command_exports_worker_env(self):
        module = load_module()
        suite_yaml = SUITE_YAML + textwrap.dedent(
            """

            image_preflight:
              project_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo
              asset_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
              default_policy: required
            worker:
              docker_host: unix:///tmp/rl/run/docker.sock
              env:
                DOCKER_API_VERSION: "1.45"
            """
        )
        suite_yaml = suite_yaml.replace(
            "    concurrency: 1\n    params:",
            "    image_manifest: manifests/images/repozero.yaml\n"
            "    concurrency: 1\n    params:",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "suite.yaml"
            suite_path.write_text(suite_yaml, encoding="utf-8")
            config = module.load_suite_config(suite_path)
            plan = module.build_run_plan(config, suite_path=suite_path, dry_run=True)

        preflight = plan["runs"][0]["image_preflight"]
        self.assertEqual(preflight["environment"]["DOCKER_API_VERSION"], "1.45")
        self.assertIn("export DOCKER_API_VERSION=1.45", preflight["command"])

    def test_image_preflight_warmup_flags_are_forwarded_to_checker(self):
        module = load_module()
        suite_yaml = SUITE_YAML + textwrap.dedent(
            """

            image_preflight:
              project_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo
              asset_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
              default_policy: required
              pull: true
              load_fallback: true
              run_smoke: true
            worker:
              docker_host: unix:///tmp/rl/run/docker.sock
            """
        )
        suite_yaml = suite_yaml.replace(
            "    concurrency: 1\n    params:",
            "    image_manifest: manifests/images/repozero.yaml\n"
            "    concurrency: 1\n    params:",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "suite.yaml"
            suite_path.write_text(suite_yaml, encoding="utf-8")
            config = module.load_suite_config(suite_path)
            plan = module.build_run_plan(config, suite_path=suite_path, dry_run=True)

        check_argv = plan["runs"][0]["image_preflight"]["commands"][0]["check_argv"]
        self.assertIn("--pull", check_argv)
        self.assertIn("--load-fallback", check_argv)
        self.assertIn("--run-smoke", check_argv)

    def test_optional_image_preflight_marks_optional_missing_fatal_in_checker_command(self):
        module = load_module()
        suite_yaml = SUITE_YAML + textwrap.dedent(
            """

            image_preflight:
              project_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo
              asset_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
              default_policy: optional
            worker:
              docker_host: unix:///tmp/rl/run/docker.sock
            """
        )
        suite_yaml = suite_yaml.replace(
            "    concurrency: 1\n    params:",
            "    image_manifest: manifests/images/deepswe.yaml\n"
            "    image_policy: optional\n"
            "    concurrency: 1\n    params:",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "suite.yaml"
            suite_path.write_text(suite_yaml, encoding="utf-8")
            config = module.load_suite_config(suite_path)
            plan = module.build_run_plan(config, suite_path=suite_path, dry_run=True)

        check_argv = plan["runs"][0]["image_preflight"]["commands"][0]["check_argv"]
        self.assertIn("--fail-on-optional-missing", check_argv)

    def test_image_preflight_project_root_can_be_relative_to_suite_file(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            manifests_dir = repo_root / "manifests"
            manifests_dir.mkdir(parents=True)
            suite_path = manifests_dir / "suite.yaml"
            suite_yaml = SUITE_YAML + textwrap.dedent(
                """

                image_preflight:
                  project_root: ..
                  asset_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
                  default_policy: required
                worker:
                  docker_host: unix:///tmp/rl/run/docker.sock
                """
            )
            suite_yaml = suite_yaml.replace(
                "    concurrency: 1\n    params:",
                "    image_manifest: manifests/images/repozero.yaml\n"
                "    concurrency: 1\n    params:",
            )
            suite_path.write_text(suite_yaml, encoding="utf-8")
            config = module.load_suite_config(suite_path)
            plan = module.build_run_plan(config, suite_path=suite_path, dry_run=True)

        preflight = plan["runs"][0]["image_preflight"]
        self.assertEqual(Path(preflight["project_root"]), repo_root)
        self.assertIn(str(repo_root), preflight["command"])

    def test_image_preflight_only_fails_when_filter_selects_no_runs(self):
        suite_yaml = textwrap.dedent(
            """
            schema_version: agentic_bench.suite.v1
            suite:
              id_prefix: empty_plan_smoke
              mode: smoke
              output_root: /tmp/agentic-foundation-model-bench/runs
            execution:
              kind: local
            worker:
              id: worker-j9jjd
              host: worker
              docker_host: unix:///tmp/rl/run/docker.sock
            active_model: dev_proxy_gpt54mini_8130
            model_profiles:
              dev_proxy_gpt54mini_8130:
                MODEL_NAME: gpt-5.4-mini
                OPENAI_BASE_URL: http://100.96.1.101:18540/v1
                OPENAI_API_KEY: env:OPENAI_API_KEY
            image_preflight:
              project_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo
              asset_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
              default_policy: required
            benchmarks:
              - id: disabled_image_bench
                script: run_disabled.sh
                adapter_status: pending_adapter
                enabled: false
                image_manifest: manifests/images/terminal_bench_2_1.yaml
                image_policy: required
            """
        ).strip()
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "suite.yaml"
            suite_path.write_text(suite_yaml, encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    str(suite_path),
                    "--image-preflight-only",
                    "--only",
                    "disabled_image_bench",
                    "--output-dir",
                    str(Path(tmpdir) / "out"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("no runs selected", proc.stderr)

    def test_execute_run_blocks_adapter_when_required_image_preflight_fails(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            adapter_marker = root / "adapter-ran"
            run = {
                "bench_id": "repozero_py2js_smoke",
                "command": "adapter command",
                "command_argv": ["bash", "-c", f"touch {adapter_marker}"],
                "image_preflight": {
                    "required": True,
                    "commands": [
                        {
                            "command": "preflight command",
                            "command_argv": ["bash", "-c", "echo preflight failed; exit 7"],
                        }
                    ],
                },
            }

            result = module._run_one(run, root / "controller")

        self.assertEqual(result["exit_code"], 7)
        self.assertEqual(result["status"], "fail:image_preflight:7")
        self.assertFalse(adapter_marker.exists())

    def test_execute_plan_parses_repozero_benchmark_status_separately(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            command = "printf 'ALL_PASS_CASES 0 / 1\nTESTS 0 / 60\nfail_example: missing generated entry file\n'"
            plan = {
                "suite_id": "unit_result_status",
                "suite_concurrency": 1,
                "run_root": str(root / "runs"),
                "runs": [
                    {
                        "schema_version": "agentic_bench.run_manifest.v1",
                        "suite_id": "unit_result_status",
                        "run_id": "unit_result_status__repozero_py2js_smoke__model",
                        "bench_id": "repozero_py2js_smoke",
                        "bench": "repozero_py2js",
                        "adapter": "repozero_py2js",
                        "adapter_status": "wired_legacy",
                        "command": command,
                        "command_argv": ["bash", "-c", command],
                    }
                ],
            }

            rc = module._execute_plan(plan, str(root / "controller"))
            summary = json.loads((root / "controller" / "summary.json").read_text(encoding="utf-8"))
            result_path = Path(summary["results"][0]["result_path"])
            parsed = json.loads(result_path.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(summary["results"][0]["status"], "pass")
        self.assertEqual(summary["results"][0]["execution_status"], "pass")
        self.assertEqual(summary["results"][0]["benchmark_status"], "fail")
        self.assertFalse(summary["results"][0]["score_claim_valid"])
        self.assertEqual(parsed["execution"]["status"], "pass")
        self.assertEqual(parsed["benchmark_result"]["status"], "fail")
        self.assertEqual(parsed["benchmark_result"]["tasks_passed"], 0)
        self.assertEqual(parsed["benchmark_result"]["tasks_total"], 1)
        self.assertEqual(parsed["benchmark_result"]["tests_passed"], 0)
        self.assertEqual(parsed["benchmark_result"]["tests_total"], 60)
        self.assertEqual(parsed["benchmark_result"]["failure_category"], "agent_generation_failed")

    def test_execute_plan_writes_summary_results_in_manifest_order(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            plan = {
                "suite_id": "unit_execute_order",
                "suite_concurrency": 2,
                "run_root": str(root / "runs"),
                "runs": [
                    {
                        "bench_id": "slow_first",
                        "adapter_status": "wired_legacy",
                        "command": "slow command",
                        "command_argv": ["bash", "-c", "sleep 0.2"],
                    },
                    {
                        "bench_id": "fast_second",
                        "adapter_status": "wired_legacy",
                        "command": "fast command",
                        "command_argv": ["bash", "-c", "true"],
                    },
                ],
            }

            rc = module._execute_plan(plan, str(root / "controller"))
            summary = json.loads((root / "controller" / "summary.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual([item["bench_id"] for item in summary["results"]], ["slow_first", "fast_second"])

    def test_image_preflight_only_runs_required_preflight_without_adapter(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            preflight_marker = root / "preflight-ran"
            adapter_marker = root / "adapter-ran"
            plan = {
                "suite_id": "unit_preflight",
                "suite_concurrency": 1,
                "run_root": str(root / "runs"),
                "runs": [
                    {
                        "bench_id": "repozero_py2js_smoke",
                        "command": "adapter command",
                        "command_argv": ["bash", "-c", f"touch {adapter_marker}"],
                        "image_preflight": {
                            "required": True,
                            "policy": "required",
                            "commands": [
                                {
                                    "command": "preflight command",
                                    "command_argv": ["bash", "-c", f"touch {preflight_marker}"],
                                }
                            ],
                        },
                    }
                ],
            }

            rc = module._execute_image_preflights(
                plan,
                str(root / "controller"),
                include_optional=False,
                fail_on_optional=False,
            )
            summary = json.loads((root / "controller" / "image_preflight_summary.json").read_text(encoding="utf-8"))
            preflight_marker_exists = preflight_marker.exists()
            adapter_marker_exists = adapter_marker.exists()

        self.assertEqual(rc, 0)
        self.assertTrue(preflight_marker_exists)
        self.assertFalse(adapter_marker_exists)
        self.assertEqual(summary["status"], 0)
        self.assertEqual(summary["counts"]["pass"], 1)
        self.assertEqual(summary["results"][0]["status"], "pass")

    def test_image_preflight_only_uses_transport_concurrency_cap(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tracker = root / "active.json"
            worker = root / "track_preflight.py"
            worker.write_text(
                textwrap.dedent(
                    """
                    import fcntl
                    import json
                    import sys
                    import time
                    from pathlib import Path

                    path = Path(sys.argv[1])

                    def update(delta):
                        path.parent.mkdir(parents=True, exist_ok=True)
                        with path.open("a+", encoding="utf-8") as handle:
                            fcntl.flock(handle, fcntl.LOCK_EX)
                            handle.seek(0)
                            raw = handle.read().strip()
                            data = json.loads(raw) if raw else {"active": 0, "max": 0}
                            data["active"] += delta
                            data["max"] = max(data["max"], data["active"])
                            handle.seek(0)
                            handle.truncate()
                            json.dump(data, handle)
                            fcntl.flock(handle, fcntl.LOCK_UN)

                    update(1)
                    time.sleep(0.2)
                    update(-1)
                    """
                ).strip(),
                encoding="utf-8",
            )
            plan = {
                "suite_id": "unit_preflight_cap",
                "suite_concurrency": 40,
                "image_preflight_concurrency": 2,
                "run_root": str(root / "runs"),
                "runs": [
                    {
                        "bench_id": f"image_{index}",
                        "command": "adapter command",
                        "command_argv": ["bash", "-c", "exit 99"],
                        "image_preflight": {
                            "required": True,
                            "policy": "required",
                            "commands": [
                                {
                                    "command": "tracked preflight",
                                    "command_argv": [sys.executable, str(worker), str(tracker)],
                                }
                            ],
                        },
                    }
                    for index in range(6)
                ],
            }

            rc = module._execute_image_preflights(
                plan,
                str(root / "controller"),
                include_optional=False,
                fail_on_optional=False,
            )
            summary = json.loads((root / "controller" / "image_preflight_summary.json").read_text(encoding="utf-8"))
            observed = json.loads(tracker.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(summary["image_preflight_concurrency"], 2)
        self.assertLessEqual(observed["max"], 2)

    def test_image_preflight_only_dedupes_identical_transport_commands(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tracker = root / "count.json"
            worker = root / "count_preflight.py"
            worker.write_text(
                textwrap.dedent(
                    """
                    import fcntl
                    import json
                    import sys
                    import time
                    from pathlib import Path

                    path = Path(sys.argv[1])
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open("a+", encoding="utf-8") as handle:
                        fcntl.flock(handle, fcntl.LOCK_EX)
                        handle.seek(0)
                        raw = handle.read().strip()
                        data = json.loads(raw) if raw else {"count": 0}
                        data["count"] += 1
                        handle.seek(0)
                        handle.truncate()
                        json.dump(data, handle)
                        fcntl.flock(handle, fcntl.LOCK_UN)
                    time.sleep(0.1)
                    """
                ).strip(),
                encoding="utf-8",
            )
            command = [sys.executable, str(worker), str(tracker)]
            plan = {
                "suite_id": "unit_preflight_dedupe",
                "suite_concurrency": 40,
                "image_preflight_concurrency": 4,
                "run_root": str(root / "runs"),
                "runs": [
                    {
                        "bench_id": bench_id,
                        "command": "adapter command",
                        "command_argv": ["bash", "-c", "exit 99"],
                        "image_preflight": {
                            "required": True,
                            "policy": "required",
                            "commands": [{"command": "same transport", "command_argv": command}],
                        },
                    }
                    for bench_id in ["first", "second"]
                ],
            }

            rc = module._execute_image_preflights(
                plan,
                str(root / "controller"),
                include_optional=False,
                fail_on_optional=False,
            )
            summary = json.loads((root / "controller" / "image_preflight_summary.json").read_text(encoding="utf-8"))
            observed = json.loads(tracker.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(summary["counts"]["pass"], 2)
        self.assertEqual(summary["image_preflight_unique_commands"], 1)
        self.assertEqual(observed["count"], 1)

    def test_image_preflight_only_skips_optional_by_default_and_can_audit_nonfatal(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            optional_marker = root / "optional-ran"
            plan = {
                "suite_id": "unit_preflight_optional",
                "suite_concurrency": 1,
                "run_root": str(root / "runs"),
                "runs": [
                    {
                        "bench_id": "swebench_optional",
                        "command": "adapter command",
                        "command_argv": ["bash", "-c", "exit 99"],
                        "image_preflight": {
                            "required": False,
                            "policy": "optional",
                            "commands": [
                                {
                                    "command": "optional preflight command",
                                    "command_argv": ["bash", "-c", f"touch {optional_marker}; exit 5"],
                                }
                            ],
                        },
                    }
                ],
            }

            skipped_rc = module._execute_image_preflights(
                plan,
                str(root / "skipped"),
                include_optional=False,
                fail_on_optional=False,
            )
            skipped_summary = json.loads((root / "skipped" / "image_preflight_summary.json").read_text(encoding="utf-8"))
            skipped_marker_exists = optional_marker.exists()
            audited_rc = module._execute_image_preflights(
                plan,
                str(root / "audited"),
                include_optional=True,
                fail_on_optional=False,
            )
            audited_summary = json.loads((root / "audited" / "image_preflight_summary.json").read_text(encoding="utf-8"))
            audited_marker_exists = optional_marker.exists()

        self.assertEqual(skipped_rc, 0)
        self.assertFalse(skipped_marker_exists)
        self.assertEqual(skipped_summary["counts"]["skipped_optional"], 1)
        self.assertEqual(skipped_summary["results"][0]["status"], "skipped_optional")
        self.assertEqual(audited_rc, 0)
        self.assertTrue(audited_marker_exists)
        self.assertEqual(audited_summary["counts"]["optional_fail"], 1)
        self.assertEqual(audited_summary["results"][0]["status"], "optional_fail:5")

    def test_example_suite_has_no_active_tau2_bench(self):
        module = load_module()
        suite_path = ROOT / "manifests" / "suite.example.yaml"
        config = module.load_suite_config(suite_path)
        active_tau2 = []
        for bench in config["benches"]:
            haystack = " ".join(str(bench.get(key, "")) for key in ("id", "benchmark", "adapter", "adapter_script"))
            if "tau2" in haystack.lower() and bench.get("enabled", True):
                active_tau2.append(bench["id"])

        self.assertEqual(active_tau2, [])

    def test_example_manifest_tau3_has_worker_ready_images_but_stays_disabled_until_adapter(self):
        module = load_module()
        suite_path = ROOT / "manifests" / "suite.example.yaml"
        config = module.load_suite_config(suite_path)
        tau3 = next(bench for bench in config["benches"] if bench["id"] == "tau3_bench")

        self.assertEqual(tau3["image_manifest"], "manifests/images/tau3_bench.yaml")
        self.assertEqual(tau3["adapter_status"], "pending_adapter")
        self.assertFalse(tau3.get("enabled", True))

        report = module.build_readiness_report(config, suite_path=suite_path, target_benches=["tau3-bench"])
        target = report["targets"][0]
        image_report = target["entries"][0]["image_manifests"][0]
        self.assertEqual(target["status"], "blocked")
        self.assertEqual(image_report["status"], "ready")
        self.assertEqual(image_report["counts"]["required_images"], 2)
        self.assertEqual(image_report["counts"]["required_without_offline_transport"], 0)
        self.assertIn("adapter_not_wired", target["blockers"])

    def test_example_manifest_has_enabled_terminal_bench_image_smoke(self):
        module = load_module()
        suite_path = ROOT / "manifests" / "suite.example.yaml"
        config = module.load_suite_config(suite_path)
        tb_smoke = next(bench for bench in config["benches"] if bench["id"] == "terminal_bench_2_1_image_smoke")

        self.assertTrue(tb_smoke.get("enabled", True))
        self.assertEqual(tb_smoke["image_manifest"], "manifests/images/terminal_bench_2_1.yaml")
        self.assertEqual(tb_smoke["image_policy"], "required")
        self.assertEqual(tb_smoke["params"]["TB_TASK_IDS"], "gcode-to-text")

        manifest = module._load_yaml((ROOT / "manifests" / "images" / "terminal_bench_2_1.yaml").read_text(encoding="utf-8"))
        required_ids = [image["id"] for image in manifest["images"] if image.get("required", True)]
        self.assertIn("terminal_bench_2_1_gcode_to_text", required_ids)
        self.assertNotIn("terminal_bench_2_1_fix_git", required_ids)

    def test_example_manifest_vitabench_one_task_smoke_uses_verified_runner(self):
        module = load_module()
        suite_path = ROOT / "manifests" / "suite.example.yaml"
        config = module.load_suite_config(suite_path)
        plan = module.build_run_plan(
            config,
            suite_path=suite_path,
            dry_run=True,
            only={"vitabench_delivery_one_task_smoke"},
            model_profile_override="dev_proxy_gpt54mini_8130",
        )

        self.assertEqual(len(plan["runs"]), 1)
        run = plan["runs"][0]
        self.assertEqual(run["bench_id"], "vitabench_delivery_one_task_smoke")
        self.assertEqual(run["script_path"], "run_vitabench.sh")
        self.assertNotEqual(run["script_path"], "run_vitabench_full.sh")
        self.assertEqual(run["model"]["profile_id"], "dev_proxy_gpt54mini_8130")
        self.assertEqual(run["runtime_env"]["BENCH_MODEL_PROFILE"], "gpt54mini_8130")
        self.assertEqual(run["runtime_env"]["OPENAI_BASE_URL"], "http://100.96.1.101:18540/v1")
        self.assertIn("run_vitabench.sh", run["command"])
        self.assertNotIn("run_vitabench_full.sh", run["command"])
        expected_params = {
            "VITA_DOMAIN": "delivery",
            "VITA_TASK_SET_NAME": "delivery",
            "VITA_TASK_IDS": 10711001,
            "NUM_TASKS": 1,
            "NUM_TRIALS": 1,
            "MAX_CONCURRENCY": 1,
            "VITA_MAX_STEPS": 20,
            "VITA_ENABLE_THINK": 0,
            "VITA_LANGUAGE": "english",
        }
        self.assertEqual(run["params"], expected_params)
        for key, value in expected_params.items():
            self.assertIn(f"{key}={value}", run["command_preview"])


    def test_readiness_report_covers_target_benches_and_blocks_unready_assets(self):
        module = load_module()
        suite_yaml = textwrap.dedent(
            """
            schema_version: agentic_bench.suite.v1
            suite:
              id: readiness_unit
              controller_host: dev
              concurrency: 4
              proxy_concurrency_ceiling: 50
              offline_policy:
                network_policy: offline_or_internal_only
                forbid_public_internet: true
                rootless_required: true
            model_profiles:
              - id: gpt54mini_8130
                model_name: gpt-5.4-mini
                provider: openai_compatible_relay
                base_url: http://8.130.49.170/v1
                api_key_env: OPENAI_API_KEY
            benches:
              - id: repozero_py2js_smoke
                benchmark: repozero_py2js
                adapter: repozero_py2js
                adapter_script: run_repozero_py2js.sh
                adapter_status: wired_legacy
                image_manifest: manifests/images/repozero.yaml
                image_policy: required
                model_profile: gpt54mini_8130
                params:
                  MAX_CONCURRENCY: 1
              - id: terminal_bench_2_1
                benchmark: terminal_bench_2_1
                adapter: terminal_bench_2_1
                adapter_script: run_terminal_bench_2_1.sh
                adapter_status: pending_adapter
                image_manifest: manifests/images/terminal_bench_2_1.yaml
                image_policy: required
                model_profile: gpt54mini_8130
              - id: mcp_atlas
                benchmark: MCP-Atlas
                adapter: mcp_atlas
                adapter_script: run_mcp_atlas.sh
                adapter_status: pending_adapter
                enabled: false
                model_profile: gpt54mini_8130
            """
        ).strip()
        repozero_manifest = textwrap.dedent(
            """
            schema_version: agentic_bench.image_manifest.v1
            bench_id: repozero_py2js_smoke
            images:
              - id: repozero_runtime
                required: true
                image_ref: 100.97.118.137:8555/swe-data-harness/repozero-runtime@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
                fallback_tar: images/repozero/runtime.tar
                fallback_tar_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
            """
        ).strip()
        tb_manifest = textwrap.dedent(
            """
            schema_version: agentic_bench.image_manifest.v1
            bench_id: terminal_bench_2_1
            images:
              - id: tb2_runtime_missing_transport
                required: true
                local_ref: tb2-offline/example:20260425
                image_transport: swe_dev_cache_identity
            """
        ).strip()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            suite_path = root / "manifests" / "suite.yaml"
            suite_path.parent.mkdir(parents=True)
            (root / "manifests" / "images").mkdir()
            suite_path.write_text(suite_yaml, encoding="utf-8")
            (root / "manifests" / "images" / "repozero.yaml").write_text(repozero_manifest, encoding="utf-8")
            (root / "manifests" / "images" / "terminal_bench_2_1.yaml").write_text(tb_manifest, encoding="utf-8")
            config = module.load_suite_config(suite_path)
            report = module.build_readiness_report(
                config,
                suite_path=suite_path,
                target_benches=["RepoZero", "Terminal Bench 2.1", "MCP-Atlas", "NL2Repo"],
            )

        by_id = {item["target_id"]: item for item in report["targets"]}
        self.assertEqual(report["schema_version"], "agentic_bench.readiness_report.v1")
        self.assertEqual(report["counts"], {"ready": 1, "blocked": 2, "missing": 1, "total": 4})
        self.assertEqual(by_id["repozero"]["status"], "ready")
        self.assertEqual(by_id["terminal_bench_2_1"]["status"], "blocked")
        self.assertIn("no_enabled_wired_adapter", by_id["terminal_bench_2_1"]["blockers"])
        self.assertIn("required_image_transport_missing", by_id["terminal_bench_2_1"]["blockers"])
        self.assertEqual(by_id["mcp_atlas"]["status"], "blocked")
        self.assertIn("no_enabled_suite_entry", by_id["mcp_atlas"]["blockers"])
        self.assertEqual(by_id["nl2repo"]["status"], "missing")
        self.assertEqual(by_id["nl2repo"]["blockers"], ["missing_suite_entry"])


    def test_readiness_helper_entry_does_not_satisfy_full_terminal_bench_target(self):
        module = load_module()
        suite_yaml = textwrap.dedent(
            """
            schema_version: agentic_bench.suite.v1
            suite:
              id: readiness_helper_unit
              controller_host: dev
            model_profiles:
              - id: gpt54mini_8130
                model_name: gpt-5.4-mini
                provider: openai_compatible_relay
            benches:
              - id: terminal_bench_2_1
                benchmark: terminal_bench_2_1
                adapter: terminal_bench_2_1
                adapter_script: run_terminal_bench_2_1.sh
                adapter_status: pending_adapter
                image_manifest: manifests/images/terminal_bench_2_1.yaml
                image_policy: required
                model_profile: gpt54mini_8130
              - id: terminal_bench_2_1_image_smoke
                benchmark: terminal_bench_2_1
                adapter: terminal_bench_2_1_image_smoke
                adapter_script: run_terminal_bench_2_1_image_smoke.sh
                adapter_status: wired_legacy
                image_manifest: manifests/images/terminal_bench_2_1_image_smoke.yaml
                image_policy: required
                model_profile: gpt54mini_8130
            """
        ).strip()
        full_manifest = textwrap.dedent(
            """
            schema_version: agentic_bench.image_manifest.v1
            bench_id: terminal_bench_2_1
            images:
              - id: tb2_full_missing_transport
                required: true
                local_ref: tb2-offline/full:20260425
                image_transport: swe_dev_cache_identity
            """
        ).strip()
        smoke_manifest = textwrap.dedent(
            """
            schema_version: agentic_bench.image_manifest.v1
            bench_id: terminal_bench_2_1_image_smoke
            images:
              - id: tb2_smoke_ready
                required: true
                image_ref: 100.97.118.137:8555/swe-data-harness/tb2-smoke@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
                fallback_tar: images/tb2/smoke.tar
                fallback_tar_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
            """
        ).strip()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            suite_path = root / "manifests" / "suite.yaml"
            suite_path.parent.mkdir(parents=True)
            (root / "manifests" / "images").mkdir()
            suite_path.write_text(suite_yaml, encoding="utf-8")
            (root / "manifests" / "images" / "terminal_bench_2_1.yaml").write_text(full_manifest, encoding="utf-8")
            (root / "manifests" / "images" / "terminal_bench_2_1_image_smoke.yaml").write_text(smoke_manifest, encoding="utf-8")
            config = module.load_suite_config(suite_path)
            report = module.build_readiness_report(config, suite_path=suite_path, target_benches=["Terminal Bench 2.1"])

        target = report["targets"][0]
        full_entry = next(entry for entry in target["entries"] if entry["bench_id"] == "terminal_bench_2_1")
        smoke_entry = next(entry for entry in target["entries"] if entry["bench_id"] == "terminal_bench_2_1_image_smoke")

        self.assertFalse(full_entry["ready"])
        self.assertTrue(smoke_entry["ready"])
        self.assertEqual(target["status"], "blocked")
        self.assertIn("adapter_not_wired", target["blockers"])
        self.assertIn("required_image_transport_missing", target["blockers"])


    def test_cli_readiness_gate_emits_json_and_fails_on_blocked_targets(self):
        suite_yaml = textwrap.dedent(
            """
            schema_version: agentic_bench.suite.v1
            suite:
              id: readiness_cli
              controller_host: dev
            model_profiles:
              - id: gpt54mini_8130
                model_name: gpt-5.4-mini
                provider: openai_compatible_relay
            benches:
              - id: repozero_py2js_smoke
                benchmark: repozero_py2js
                adapter: repozero_py2js
                adapter_script: run_repozero_py2js.sh
                adapter_status: wired_legacy
                model_profile: gpt54mini_8130
            """
        ).strip()
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = Path(tmpdir) / "suite.yaml"
            suite_path.write_text(suite_yaml, encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    str(suite_path),
                    "--readiness",
                    "--json",
                    "--target-benches",
                    "RepoZero,NL2Repo",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stderr, "")
        report = json.loads(proc.stdout)
        self.assertEqual(report["schema_version"], "agentic_bench.readiness_report.v1")
        self.assertEqual(report["counts"], {"ready": 1, "blocked": 0, "missing": 1, "total": 2})
        self.assertEqual([target["target_id"] for target in report["targets"]], ["repozero", "nl2repo"])
        self.assertEqual(report["targets"][1]["blockers"], ["missing_suite_entry"])


    def test_terminal_bench_full_entry_uses_cache_manifest_with_current_gap_counts(self):
        module = load_module()
        suite_path = ROOT / "manifests" / "suite.example.yaml"
        config = module.load_suite_config(suite_path)
        tb_full = next(bench for bench in config["benches"] if bench["id"] == "terminal_bench_2_1")

        self.assertEqual(tb_full["image_manifest"], "manifests/images/terminal_bench_2_1_swe_dev_cache.yaml")
        report = module.build_readiness_report(config, suite_path=suite_path, target_benches=["Terminal Bench 2.1"])
        tb_target = report["targets"][0]
        full_entry = next(entry for entry in tb_target["entries"] if entry["bench_id"] == "terminal_bench_2_1")
        manifest_counts = full_entry["image_manifests"][0]["counts"]

        self.assertEqual(manifest_counts["required_images"], 89)
        self.assertEqual(manifest_counts["required_with_offline_transport"], 82)
        self.assertEqual(manifest_counts["required_without_offline_transport"], 7)
        self.assertIn("required_image_transport_missing", full_entry["blockers"])

        cache_manifest = module._load_yaml((ROOT / "manifests" / "images" / "terminal_bench_2_1_swe_dev_cache.yaml").read_text(encoding="utf-8"))
        self.assertEqual(cache_manifest["evidence"]["offline_transport_ready_count"], 82)
        self.assertEqual(cache_manifest["evidence"]["remaining_transport_gap_count"], 7)
        blockers = cache_manifest["known_blockers"]
        self.assertIn("missing_transport_for_7_cache_tasks", blockers)
        self.assertNotIn("missing_transport_for_39_cache_only_tasks", blockers)


    def test_readiness_resolves_manifests_from_image_preflight_project_root(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            manifests_dir = repo_root / "manifests" / "images"
            manifests_dir.mkdir(parents=True)
            (manifests_dir / "repozero.yaml").write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: repozero_py2js_smoke
                    images:
                      - id: repozero_runtime
                        required: true
                        image_ref: 100.97.118.137:8555/swe-data-harness/repozero-runtime@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
                    """
                ).strip(),
                encoding="utf-8",
            )
            suite_path = root / "tmp_suite.yaml"
            suite_path.write_text(
                textwrap.dedent(
                    f"""
                    schema_version: agentic_bench.suite.v1
                    suite:
                      id: readiness_external_suite
                      controller_host: dev
                    model_profiles:
                      - id: gpt54mini_8130
                        model_name: gpt-5.4-mini
                        provider: openai_compatible_relay
                    image_preflight:
                      project_root: {repo_root}
                    benches:
                      - id: repozero_py2js_smoke
                        benchmark: repozero_py2js
                        adapter: repozero_py2js
                        adapter_script: run_repozero_py2js.sh
                        adapter_status: wired_legacy
                        image_manifest: manifests/images/repozero.yaml
                        image_policy: required
                        model_profile: gpt54mini_8130
                    """
                ).strip(),
                encoding="utf-8",
            )
            config = module.load_suite_config(suite_path)
            report = module.build_readiness_report(config, suite_path=suite_path, target_benches=["RepoZero"])

        self.assertEqual(report["counts"], {"ready": 1, "blocked": 0, "missing": 0, "total": 1})
        target = report["targets"][0]
        self.assertEqual(target["status"], "ready")
        manifest_report = target["entries"][0]["image_manifests"][0]
        self.assertEqual(Path(manifest_report["path"]).parent.name, "images")
        self.assertNotIn("image_manifest_missing", target["blockers"])


if __name__ == "__main__":
    unittest.main()
