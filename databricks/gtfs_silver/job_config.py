"""Genera la configuración del Job sin credenciales y sin llamar a Databricks."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path, PurePosixPath

SNAPSHOTS = [
    {"entity": "agency", "feed_version": "2025-10-28",
     "snapshot_sha256": "07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952"},
    {"entity": "agency", "feed_version": "2026-09-29",
     "snapshot_sha256": "08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097"},
]


def build_job(repo_root: str, *, environment_version: str = "4") -> dict:
    root = PurePosixPath(repo_root)
    if (not repo_root.startswith("/Workspace/") or ".." in root.parts
            or "\\" in repo_root or "\n" in repo_root or "\r" in repo_root):
        raise ValueError("repo_root debe ser una ruta absoluta de /Workspace/ al repositorio.")
    if not environment_version.isdigit():
        raise ValueError("environment_version debe ser un número de versión serverless.")
    requirements = Path(__file__).resolve().parents[1] / "requirements-silver.txt"
    dependencies = [line.strip() for line in requirements.read_text().splitlines()
                    if line.strip() and not line.lstrip().startswith("#")]
    job = {
        "name": "gtfs_bogota_silver_manual",
        "description": "Valida y publica snapshots habilitados, con auditoría y cuarentena. Sin calendario automático.",
        "max_concurrent_runs": 1,
        "queue": {"enabled": True},
        "parameters": [
            {"name": "catalog", "default": "workspace"},
            {"name": "schema", "default": "gtfs_bogota"},
            {"name": "staging_volume", "default": "staging_gtfs"},
            {"name": "mode", "default": "publish"},
            {"name": "verify_history", "default": "true"},
            {"name": "work_items", "default": json.dumps(SNAPSHOTS, separators=(",", ":"))},
        ],
        "environments": [{
            "environment_key": "silver",
            "spec": {"environment_version": environment_version, "dependencies": dependencies},
        }],
        "tasks": [{
            "task_key": "publish_snapshots",
            "for_each_task": {
                "inputs": "{{job.parameters.work_items}}", "concurrency": 1,
                "task": {
                    "task_key": "process_entity_snapshot",
                    "notebook_task": {
                        "notebook_path": str(root / "databricks/notebooks/silver/10_publish_gtfs_entity.ipynb"),
                        "source": "WORKSPACE",
                        "base_parameters": {
                            "repo_root": str(root),
                            **{name: "{{job.parameters." + name + "}}" for name in (
                                "catalog", "schema", "staging_volume", "mode", "verify_history",
                            )},
                            **{name: "{{input." + name + "}}" for name in (
                                "entity", "feed_version", "snapshot_sha256",
                            )},
                        },
                    },
                    "environment_key": "silver",
                    "timeout_seconds": 1800,
                    "max_retries": 1, "min_retry_interval_millis": 60000,
                },
            },
        }],
    }

    # Serializo también stops para evitar escritores concurrentes en la auditoría común.
    # Stops no tiene una dependencia de datos con routes: su jerarquía es interna.
    # Calendar_dates requiere calendar cuando el archivo semanal está publicado.
    for entity, predecessor in (("routes", "publish_snapshots"), ("stops", "publish_routes"),
                                ("calendar", "publish_stops"), ("calendar_dates", "publish_calendar")):
        items = [{**item, "entity": entity} for item in SNAPSHOTS]
        parameter = f"{entity}_work_items"
        job["parameters"].append({"name": parameter, "default": json.dumps(items, separators=(",", ":"))})
        task = deepcopy(job["tasks"][0])
        task["task_key"] = f"publish_{entity}"
        task["depends_on"] = [{"task_key": predecessor}]
        task["for_each_task"]["inputs"] = "{{job.parameters." + parameter + "}}"
        task["for_each_task"]["task"]["task_key"] = f"process_{entity}_snapshot"
        job["tasks"].append(task)
    return job


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, help="Ruta absoluta del repositorio en Workspace.")
    parser.add_argument("--environment-version", default="4", help="Versión serverless disponible en el workspace.")
    parser.add_argument("--output", type=Path, help="Archivo JSON de salida; si se omite, imprime JSON.")
    args = parser.parse_args()
    result = json.dumps(build_job(args.repo_root, environment_version=args.environment_version),
                        ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
