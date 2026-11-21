"""Resuelve rutas e IDs de la plantilla; genera archivos locales y nunca llama a Databricks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath

TEMPLATE = Path(__file__).with_name("gtfs_bogota_pipeline.template.json")


def workspace_path(value: str) -> str:
    path = PurePosixPath(value)
    if (not value.startswith("/Workspace/") or len(path.parts) < 3 or ".." in path.parts
            or any(char in value for char in ("\\", "\n", "\r", "{", "}", "\x00"))
            or value.startswith("/Workspace/REPO_ROOT")):
        raise ValueError("Usa una ruta real y absoluta de /Workspace/, sin marcadores ni referencias dinámicas.")
    return str(path)


def render_job(repo_root: str, bronze_job_id: int, silver_job_id: int, *,
               discovery_notebook_path: str | None = None, environment_version: str = "4") -> dict:
    root = workspace_path(repo_root)
    for label, value in (("bronze_job_id", bronze_job_id), ("silver_job_id", silver_job_id)):
        if type(value) is not int or not 0 < value <= 9223372036854775807:
            raise ValueError(f"{label} debe ser un ID entero positivo del Job existente.")
    if bronze_job_id == silver_job_id:
        raise ValueError("Bronze y Silver deben identificar Jobs distintos.")
    if not environment_version.isdigit():
        raise ValueError("environment_version debe indicar una versión serverless disponible.")
    job = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    for parameter in job["parameters"]:
        if parameter["name"] == "repo_root":
            parameter["default"] = root
    discovery = job["tasks"][0]["notebook_task"]
    discovery["notebook_path"] = (workspace_path(discovery_notebook_path) if discovery_notebook_path else
                                  root + "/databricks/notebooks/06_discover_static_gtfs_catalog")
    job["environments"][0]["spec"]["environment_version"] = environment_version
    job["tasks"][2]["for_each_task"]["task"]["run_job_task"]["job_id"] = bronze_job_id
    job["tasks"][3]["run_job_task"]["job_id"] = silver_job_id
    return job


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--bronze-job-id", required=True, type=int)
    parser.add_argument("--silver-job-id", required=True, type=int)
    parser.add_argument("--discovery-notebook-path", help="Ruta exacta de notebook 06 si difiere del default.")
    parser.add_argument("--environment-version", default="4")
    parser.add_argument("--output", type=Path, required=True, help="JSON local resuelto para CLI/API.")
    parser.add_argument("--yaml-output", type=Path, help="Representación resources.jobs para el editor YAML/bundles.")
    args = parser.parse_args()
    if args.yaml_output and args.output.resolve() == args.yaml_output.resolve():
        parser.error("El JSON y el YAML necesitan rutas distintas.")
    job = render_job(args.repo_root, args.bronze_job_id, args.silver_job_id,
                     discovery_notebook_path=args.discovery_notebook_path, environment_version=args.environment_version)
    args.output.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.yaml_output:
        # YAML 1.2 acepta este documento JSON, sin una dependencia adicional de Python.
        wrapper = {"resources": {"jobs": {"gtfs_bogota_pipeline": job}}}
        args.yaml_output.write_text(json.dumps(wrapper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Configuración generada: {args.output}. No creé ni ejecuté ningún Job.")


if __name__ == "__main__":
    main()
