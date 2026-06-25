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
        self.assertIn("OPENAI_API_KEY", json.dumps(plan, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
