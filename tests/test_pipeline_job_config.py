"""Contrato local del coordinador; no sustituye el piloto del motor Lakeflow."""
import importlib.util
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline_renderer", ROOT / "databricks/jobs/render_pipeline.py")
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


def job():
    return renderer.render_job("/Workspace/fixture", 101, 202)


def task_map(configuration):
    return {task["task_key"]: task for task in configuration["tasks"]}


class PipelineJobConfigTests(unittest.TestCase):
    def test_calls_existing_jobs_with_separate_request_and_raw_identity(self):
        configuration = job(); tasks = task_map(configuration)
        bronze = tasks["ingest_bronze"]["for_each_task"]["task"]["run_job_task"]
        silver = tasks["publish_silver"]["run_job_task"]
        self.assertEqual((bronze["job_id"], silver["job_id"]), (101, 202))
        self.assertEqual(bronze["job_parameters"]["requested_feed_version"], "{{input.feed_version}}")
        self.assertEqual(bronze["job_parameters"]["coordinator_run_id"], "{{job.run_id}}")
        names = {p["name"] for p in configuration["parameters"]}
        self.assertFalse({"feed_version", "snapshot_sha256", "requested_feed_version"} & names)
        self.assertNotIn("snapshot_sha256", bronze["job_parameters"])
        self.assertNotIn("snapshot_sha256", silver["job_parameters"])
        self.assertEqual(tasks["ingest_bronze"]["for_each_task"]["concurrency"], 1)
        self.assertEqual(configuration["max_concurrent_runs"], 1)
        self.assertNotIn("schedule", configuration)
        self.assertNotIn("trigger", configuration)

    def test_no_work_join_and_failures_follow_documented_dependency_rules(self):
        tasks = task_map(job())
        self.assertEqual(tasks["ingest_bronze"]["depends_on"], [{"task_key": "has_bronze_work", "outcome": "true"}])
        condition = tasks["has_bronze_work"]["condition_task"]
        self.assertEqual(condition, {"op": "GREATER_THAN", "left": "{{tasks.plan_bronze.values.planned_count}}", "right": "0"})
        silver = tasks["publish_silver"]
        self.assertEqual(silver["run_if"], "NONE_FAILED")
        # Modelo de aceptación de las reglas documentadas; el motor real se prueba en Workspace.
        def eligible(states):
            direct = [states[d["task_key"]] for d in silver["depends_on"]]
            return (all(s in {"SUCCEEDED", "EXCLUDED"} for s in direct)
                    and any(s == "SUCCEEDED" for s in direct))
        for state, expected in (("EXCLUDED", True), ("SUCCEEDED", True), ("FAILED", False),
                                ("UPSTREAM_FAILED", False), ("CANCELED", False)):
            with self.subTest(bronze=state):
                self.assertEqual(eligible({"plan_bronze": "SUCCEEDED", "has_bronze_work": "SUCCEEDED", "ingest_bronze": state}), expected)
        self.assertFalse(eligible({"plan_bronze": "FAILED", "has_bronze_work": "UPSTREAM_FAILED", "ingest_bronze": "UPSTREAM_FAILED"}))

    def test_condition_edges_require_outcomes_and_silver_joins_outside_the_branch(self):
        tasks = task_map(job())
        conditions = {name for name, task in tasks.items() if "condition_task" in task}
        for name, task in tasks.items():
            for dependency in task.get("depends_on", []):
                if dependency["task_key"] in conditions:
                    with self.subTest(task=name, source=dependency["task_key"]):
                        self.assertIn(dependency.get("outcome"), {"true", "false"})
        silver = tasks["publish_silver"]
        # El plan ejecutado evita la exclusión en cascada cuando Bronze no tiene trabajo.
        self.assertEqual({d["task_key"] for d in silver["depends_on"]}, {"plan_bronze", "ingest_bronze"})
        self.assertEqual(silver["run_if"], "NONE_FAILED")

    def test_references_and_dag_resolve_without_child_task_values(self):
        configuration = job(); tasks = task_map(configuration)
        names = {p["name"] for p in configuration["parameters"]}
        for name in re.findall(r"\{\{job\.parameters\.([A-Za-z0-9_]+)\}\}", json.dumps(configuration)):
            self.assertIn(name, names)
        allowed_values = {"planned_count", "ingestion_work_items"}
        for source, value in re.findall(r"\{\{tasks\.([A-Za-z0-9_]+)\.values\.([A-Za-z0-9_]+)\}\}", json.dumps(configuration)):
            self.assertEqual(source, "plan_bronze")
            self.assertIn(value, allowed_values)
        seen = set()
        for task in configuration["tasks"]:
            self.assertTrue({d["task_key"] for d in task.get("depends_on", [])} <= seen)
            seen.add(task["task_key"])
        self.assertEqual(seen, {"plan_bronze", "has_bronze_work", "ingest_bronze", "publish_silver"})
        self.assertEqual(tasks["publish_silver"]["run_job_task"]["job_parameters"]["feed_version_from"], "{{job.parameters.silver_feed_version_from}}")

    def test_invalid_environment_ids_and_paths_fail_before_writing(self):
        for bronze, silver in ((0, 202), (True, 202), (101, 101), (101, -1), (101, "202")):
            with self.subTest(ids=(bronze, silver)), self.assertRaises(ValueError):
                renderer.render_job("/Workspace/fixture", bronze, silver)
        for root in ("C:\\fixture", "/Workspace/REPO_ROOT", "/Workspace/a/../b", "/Workspace/a\n", "/Workspace/{{job.id}}"):
            with self.subTest(root=root), self.assertRaises(ValueError):
                renderer.render_job(root, 101, 202)
        with self.assertRaises(ValueError):
            renderer.render_job("/Workspace/fixture", 101, 202, environment_version="invalid")
        rendered = renderer.render_job("/Workspace/fixture", 101, 202, discovery_notebook_path="/Workspace/fixture/06.ipynb")
        self.assertEqual(rendered["tasks"][0]["notebook_task"]["notebook_path"], "/Workspace/fixture/06.ipynb")

    def test_cli_outputs_equivalent_json_and_yaml_without_remote_calls(self):
        with TemporaryDirectory(prefix="gtfs-config-") as temporary:
            output, yaml_output = Path(temporary) / "job.json", Path(temporary) / "job.yaml"
            args = ["render_pipeline.py", "--repo-root", "/Workspace/fixture", "--bronze-job-id", "101",
                    "--silver-job-id", "202", "--output", str(output), "--yaml-output", str(yaml_output)]
            with patch("sys.argv", args):
                renderer.main()
            configuration = json.loads(output.read_text(encoding="utf-8"))
            # El archivo YAML usa el subconjunto JSON de YAML 1.2.
            wrapper = json.loads(yaml_output.read_text(encoding="utf-8"))
            self.assertEqual(wrapper["resources"]["jobs"]["gtfs_bogota_pipeline"], configuration)
            self.assertNotIn("REPO_ROOT", json.dumps(configuration))
            self.assertEqual(configuration["tasks"][0]["notebook_task"]["base_parameters"]["emit_task_values"], "true")
