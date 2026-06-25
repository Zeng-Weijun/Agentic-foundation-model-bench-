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
      - id: tau2_smoke
        benchmark: tau2
        adapter: tau2
        adapter_status: todo
        model_profile: gpt54mini_8130
        worker_host: worker
        concurrency: 1
        params:
          num_tasks: 1
          num_trials: 1
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
      - id: tau2_paper_core
        script: run_tau2_paper_core.sh
        adapter_status: existing_legacy
        modes: [smoke, full]
        env_by_mode:
          smoke:
            NUM_TASKS: "1"
            NUM_TRIALS: "1"
          full:
            NUM_TASKS: all
      - id: repozero_py2js
        script: run_repozero_py2js.sh
        adapter_status: existing_legacy
        modes: [smoke, full]
        env_by_mode:
          smoke:
            REPOZERO_MODE: smoke
    """
).strip()


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
        self.assertEqual(plan["runs"][0]["adapter_status"], "todo")
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
                    "tau2_paper_core",
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
        self.assertEqual(plan["runs"][0]["bench_id"], "tau2_paper_core")
        self.assertEqual(plan["runs"][0]["worker_host"], "worker")
        self.assertEqual(plan["runs"][0]["model"]["profile_id"], "relay_gpt54mini_8130")
        self.assertEqual(plan["runs"][0]["params"]["NUM_TASKS"], "1")
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
                only={"tau2_paper_core"},
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


if __name__ == "__main__":
    unittest.main()
