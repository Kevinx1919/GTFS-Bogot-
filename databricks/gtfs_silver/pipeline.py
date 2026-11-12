"""Una ejecución por entidad y snapshot; el Job reutiliza las mismas reglas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agency_validation import SnapshotSpec, read_source_header
from .agency_spark import read_and_validate
from .publication import (
    PublicationTables, _versioned_table, publish_agency, publish_snapshot, quoted_table, simple_identifier,
)
from . import routes_spark, stops_spark, calendars_spark, service_dates_spark, shape_points_spark
from .models import DerivedSnapshotSpec, SOURCE_ENTITY_NAMES

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "silver_entities.json"


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        raise ValueError("El registro de entidades debe ser un objeto JSON.")
    return registry


def run_entity(spark, *, catalog: str, schema: str, staging_volume: str,
               entity: str, feed_version: str, snapshot_sha256: str,
               mode: str = "publish", verify_history: bool = True,
               window_start: str = "", window_end: str = "",
               run_id: str | None = None) -> dict[str, Any]:
    for value in (catalog, schema, staging_volume, entity):
        simple_identifier(value)
    configuration = load_registry().get(entity)
    if not configuration or not configuration["enabled"]:
        raise ValueError(f"No hay un contrato habilitado para {entity}.")
    if entity == "service_dates":
        if configuration["validator"] != "service_dates_v1":
            raise ValueError("La derivación requiere el contrato service_dates_v1.")
        if mode not in {"validate", "publish"}:
            raise ValueError("mode debe ser validate o publish.")
        spec = DerivedSnapshotSpec(feed_version, snapshot_sha256, window_start, window_end)
        spark.conf.set("spark.sql.session.timeZone", "UTC")
        return _run_service_dates(spark, catalog, schema, spec, mode, verify_history, run_id)
    validators = {"agency": "agency_v1", "routes": "routes_v1", "stops": "stops_v1",
                  "calendar": "calendar_v1", "calendar_dates": "calendar_dates_v1",
                  "shape_points": "shape_points_v1"}
    if entity not in validators or configuration["validator"] != validators[entity]:
        raise ValueError("La entidad todavía no tiene procesador implementado.")
    source_entity = SOURCE_ENTITY_NAMES.get(entity, entity)
    if configuration["bronze_table"] != f"bronze_gtfs_{source_entity}":
        raise ValueError("El registro no corresponde a la tabla Bronze de la entidad.")
    if mode not in {"validate", "publish"}:
        raise ValueError("mode debe ser validate o publish.")
    maximum = configuration.get("max_driver_rows")
    if entity == "agency" and (type(maximum) is not int or not 1 <= maximum <= 1000):
        raise ValueError("El límite del procesador pequeño de agency debe estar entre 1 y 1.000.")
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    source_path = (
        f"/Volumes/{catalog}/{schema}/{staging_volume}/gtfs_static/"
        f"feed_version={feed_version}/sha256={snapshot_sha256}/{source_entity}.txt"
    )
    spec = SnapshotSpec(feed_version, snapshot_sha256, source_path, entity)
    processors = {"routes": routes_spark, "stops": stops_spark,
                  "calendar": calendars_spark, "calendar_dates": calendars_spark,
                  "shape_points": shape_points_spark}
    header_reader = read_source_header if entity == "agency" else processors[entity].read_source_header
    columns = header_reader(source_path)
    bronze = f"{catalog}.{schema}.{configuration['bronze_table']}"
    if not spark.catalog.tableExists(quoted_table(bronze)):
        raise ValueError("No existe Bronze para la entidad seleccionada.")
    # Fijar versiones Delta evita que acciones posteriores lean otro estado de entrada.
    source = _versioned_table(spark, bronze)
    if entity in processors:
        dependencies = []
        if entity == "routes":
            dependency = f"{catalog}.{schema}.silver_gtfs_agency"
            if not spark.catalog.tableExists(quoted_table(dependency)):
                raise ValueError("Publica agency en Silver antes de procesar routes.")
            dependencies.append(_versioned_table(spark, dependency))
        options = {}
        if entity == "calendar_dates":
            weekly_published = calendars_spark.calendar_source_present(source_path)
            options["calendar_published"] = weekly_published
            if weekly_published:
                dependency = f"{catalog}.{schema}.silver_gtfs_calendar"
                if not spark.catalog.tableExists(quoted_table(dependency)):
                    raise ValueError("Publica calendar en Silver antes de sus excepciones del mismo snapshot.")
                dependencies.append(_versioned_table(spark, dependency))
            else:
                # Una pérdida de Staging no equivale a una ausencia legítima del archivo.
                weekly_bronze = f"{catalog}.{schema}.bronze_gtfs_calendar"
                if spark.catalog.tableExists(quoted_table(weekly_bronze)):
                    from pyspark.sql import functions as F
                    weekly_rows = _versioned_table(spark, weekly_bronze).filter(
                        F.col("source_sha256") == snapshot_sha256).limit(1).count()
                    if weekly_rows:
                        raise ValueError("Falta calendar.txt en Staging, pero Bronze tiene filas de su hash. "
                                         "Revisa Staging; no lo interpretaré como un archivo no publicado.")
        result = processors[entity].read_and_validate(source, columns, spec, *dependencies, **options)
        return publish_snapshot(
            spark, result, spec, PublicationTables(catalog, schema, entity),
            mode=mode, verify_history=verify_history, run_id=run_id,
        )
    result = read_and_validate(source, columns, spec, maximum)
    return publish_agency(
        spark, result, spec, PublicationTables(catalog, schema, entity),
        mode=mode, verify_history=verify_history, run_id=run_id,
    )


def _run_service_dates(spark, catalog, schema, spec, mode, verify_history, run_id):
    """Resuelve fuentes publicadas desde auditoría; la derivación no simula un TXT."""
    from pyspark.sql import functions as F
    observations = f"{catalog}.{schema}.audit_gtfs_source_schema_observations"
    if not spark.catalog.tableExists(quoted_table(observations)):
        raise ValueError("Falta la auditoría de encabezados para identificar las fuentes publicadas del snapshot.")
    names = (spark.table(quoted_table(observations))
             .filter((F.col("source_feed_version") == spec.feed_version) & (F.col("source_sha256") == spec.sha256)
                     & F.col("source_file_name").isin("calendar.txt", "calendar_dates.txt"))
             .select("source_file_name").distinct().limit(2).collect())
    published = {r.source_file_name.removesuffix(".txt") for r in names}
    if not published:
        raise ValueError("La auditoría no declara fuentes de calendario para este snapshot.")
    sources = {"calendar": None, "calendar_dates": None}
    references = {}
    for entity in sorted(published):
        table = f"{catalog}.{schema}.silver_gtfs_{entity}"
        if not spark.catalog.tableExists(quoted_table(table)):
            raise ValueError(f"Publica primero {entity}_v1 del mismo snapshot.")
        frame, version = _versioned_table(spark, table, with_version=True)
        sources[entity] = frame
        references[entity + "_table"] = table
        references[entity + "_delta_version"] = str(version)
    result = service_dates_spark.derive_service_dates(spark, spec, sources["calendar"], sources["calendar_dates"], references)
    tables = PublicationTables(catalog, schema, "service_dates")
    if spark.catalog.tableExists(quoted_table(tables.name("silver"))):
        service_dates_spark.check_existing_window(_versioned_table(spark, tables.name("silver")), spec)
    return publish_snapshot(spark, result, spec, tables, mode=mode, verify_history=verify_history, run_id=run_id)
