"""Una ejecución por entidad y snapshot; el Job reutiliza las mismas reglas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agency_validation import SnapshotSpec, read_source_header
from .agency_spark import read_and_validate
from .publication import PublicationTables, publish_agency, quoted_table, simple_identifier

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "silver_entities.json"


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        raise ValueError("El registro de entidades debe ser un objeto JSON.")
    return registry


def run_entity(spark, *, catalog: str, schema: str, staging_volume: str,
               entity: str, feed_version: str, snapshot_sha256: str,
               mode: str = "publish", verify_history: bool = True,
               run_id: str | None = None) -> dict[str, Any]:
    for value in (catalog, schema, staging_volume, entity):
        simple_identifier(value)
    configuration = load_registry().get(entity)
    if not configuration or not configuration["enabled"]:
        raise ValueError(f"No hay un contrato habilitado para {entity}.")
    if entity != "agency" or configuration["validator"] != "agency_v1":
        raise ValueError("La entidad todavía no tiene procesador implementado.")
    if configuration["bronze_table"] != f"bronze_gtfs_{entity}":
        raise ValueError("El registro no corresponde a la tabla Bronze de la entidad.")
    if mode not in {"validate", "publish"}:
        raise ValueError("mode debe ser validate o publish.")
    maximum = configuration["max_driver_rows"]
    if not isinstance(maximum, int) or not 1 <= maximum <= 1000:
        raise ValueError("El límite del procesador pequeño de agency debe estar entre 1 y 1.000.")
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    source_path = (
        f"/Volumes/{catalog}/{schema}/{staging_volume}/gtfs_static/"
        f"feed_version={feed_version}/sha256={snapshot_sha256}/agency.txt"
    )
    spec = SnapshotSpec(feed_version, snapshot_sha256, source_path)
    columns = read_source_header(source_path)
    bronze = quoted_table(f"{catalog}.{schema}.{configuration['bronze_table']}")
    if not spark.catalog.tableExists(bronze):
        raise ValueError("No existe Bronze para la entidad seleccionada.")
    result = read_and_validate(spark.table(bronze), columns, spec, maximum)
    return publish_agency(
        spark, result, spec, PublicationTables(catalog, schema, entity),
        mode=mode, verify_history=verify_history, run_id=run_id,
    )
