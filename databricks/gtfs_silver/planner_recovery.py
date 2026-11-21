"""Resoluciones explícitas de intentos abandonados; no modifica tablas analíticas."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from gtfs_bronze.runtime import immutable_insert
from .planner import bronze_snapshots, identity, timestamp
from .publication import _versioned_table, quoted_table, simple_identifier

RESOLUTION_DDL = """
resolution_id string, layer string, entity string, source_feed_version string, source_sha256 string,
attempt_run_id string, observed_started_at_utc timestamp, resolution_kind string, reason string,
reference_run_id string, resolved_at_utc timestamp, resolved_by string, evidence_json string
"""
RESOLUTION_FIELDS = tuple(part.strip().split()[0] for part in RESOLUTION_DDL.split(","))


def load_resolutions(spark: Any, catalog: str, schema: str, limit: int) -> tuple[Any | None, int | None]:
    from .planner_runtime import bounded_rows
    table = f"{catalog}.{schema}.audit_gtfs_attempt_resolutions"
    if not spark.catalog.tableExists(quoted_table(table)): return None, None
    frame, version = _versioned_table(spark, table, with_version=True)
    rows = bounded_rows(frame.select(*RESOLUTION_FIELDS), limit, "Resoluciones de intentos")
    for row in rows:
        identity(row)
        if (row["layer"], row["resolution_kind"]) not in {("bronze", "INVALID_IDENTITY"), ("silver", "ABANDONED")}:
            raise ValueError("Tipo de resolución desconocido; revisar antes de planificar.")
        if not all(row.get(key) for key in ("resolution_id", "attempt_run_id", "reason", "resolved_by", "evidence_json", "reference_run_id")):
            raise ValueError("Resolución incompleta.")
        timestamp(row["observed_started_at_utc"]); timestamp(row["resolved_at_utc"])
    return frame.select(*RESOLUTION_FIELDS), version


def exclude_resolved(frame: Any, resolutions: Any | None, *, layer: str, closed: Any | None = None,
                     limit: int = 5000) -> tuple[Any, list[dict]]:
    """Excluye solo el estado observado. Si el intento cambia o termina, vuelve a evaluarse."""
    from pyspark.sql import functions as F
    from .planner_runtime import bounded_rows
    if resolutions is None: return frame, []
    selected = resolutions.filter(F.col("layer") == layer).alias("r")
    original = frame.alias("t")
    run_column = "quality_run_id" if layer == "bronze" else "silver_run_id"
    condition = ((F.col("t." + run_column) == F.col("r.attempt_run_id"))
                 & (F.col("t.source_feed_version") == F.col("r.source_feed_version"))
                 & (F.col("t.source_sha256") == F.col("r.source_sha256"))
                 & (F.col("t.started_at_utc") == F.col("r.observed_started_at_utc"))
                 & (F.col("t.status") == "RUNNING"))
    if layer == "silver":
        condition = condition & (F.col("t.entity") == F.col("r.entity")) & (F.col("t.silver_committed") == False) & F.col("t.finished_at_utc").isNull()
    else:
        condition = condition & (F.col("r.entity") == "*") & F.col("t.completed_at_utc").isNull()
    matched = original.join(selected, condition, "inner")
    fields = ["resolution_id", "layer", "entity", "source_feed_version", "source_sha256", "attempt_run_id", "resolution_kind"]
    applied = matched.select(*[F.col("r." + key).alias(key) for key in fields]).distinct()
    if layer == "bronze":
        # Un CLOSED posterior invalida la exclusión: no oculto una validación que terminó.
        applied = applied.join(closed.select(F.col("quality_run_id").alias("attempt_run_id")).distinct(), "attempt_run_id", "left_anti")
    rows = bounded_rows(applied, limit, "Resoluciones aplicadas")
    if not rows: return frame, []
    keys = ["source_feed_version", "source_sha256", run_column]
    if layer == "silver": keys.insert(0, "entity")
    excluded = applied.select(*[F.col("attempt_run_id").alias(run_column) if key == run_column else F.col(key) for key in keys]).distinct()
    return frame.join(excluded, keys, "left_anti"), rows


def resolve_attempt(spark: Any, *, catalog: str, schema: str, layer: str, entity: str,
                    feed_version: str, sha256: str, attempt_run_id: str, reason: str,
                    mode: str = "preview", executions_stopped: bool = False) -> dict:
    """Prepara o inserta una resolución respaldada por evidencia que se vuelve a leer."""
    from .planner_runtime import _target_states, bounded_rows, read_bronze_events
    for value in (catalog, schema): simple_identifier(value)
    identity({"source_feed_version": feed_version, "source_sha256": sha256})
    if mode not in {"preview", "apply"} or layer not in {"bronze", "silver"}:
        raise ValueError("Usa mode=preview/apply y layer=bronze/silver.")
    if not reason.strip() or len(reason) > 1000:
        raise ValueError("Escribe un motivo concreto de hasta 1000 caracteres.")
    if mode == "apply" and executions_stopped is not True:
        raise ValueError("La resolución requiere que las ejecuciones hayan terminado o se hayan detenido.")
    from pyspark.sql import functions as F
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    if layer == "bronze":
        if entity != "*": raise ValueError("Una resolución Bronze corresponde al snapshot completo: entity=*.")
        events, _ = read_bronze_events(spark, f"{catalog}.{schema}.audit_gtfs_bronze_snapshot_runs", limit=5000)
        snapshots = bronze_snapshots(events)
        candidate = [item for item in snapshots if item["key"] == (feed_version, sha256)]
        if (len(candidate) != 1 or candidate[0]["start"]["quality_run_id"] != attempt_run_id
                or candidate[0]["closure"] is not None or candidate[0]["reason"] != "INCOMPLETE_BRONZE_ATTEMPT"):
            raise ValueError("El intento Bronze no es el último incompleto esperado; no resolver.")
        known_hash = [item for item in snapshots if not item["reason"] and item["key"][1] == sha256 and item["key"][0] != feed_version]
        correct_version = [item for item in snapshots if not item["reason"] and item["key"][0] == feed_version and item["key"][1] != sha256]
        if len(known_hash) != 1 or len(correct_version) != 1:
            raise ValueError("Falta evidencia inequívoca de ambas identidades correctas; no resolver automáticamente.")
        observed = candidate[0]["start"]
        kind = "INVALID_IDENTITY"
        reference = correct_version[0]["start"]["quality_run_id"]
        evidence = {"hash_bound_to_version": known_hash[0]["key"][0],
                    "canonical_quality_run_id": reference, "canonical_sha256": correct_version[0]["key"][1]}
    else:
        simple_identifier(entity)
        table = f"{catalog}.{schema}.audit_gtfs_silver_runs"
        audit, _ = _versioned_table(spark, table, with_version=True)
        scope = ((F.col("entity") == entity) & (F.col("source_feed_version") == feed_version) & (F.col("source_sha256") == sha256))
        rows = bounded_rows(audit.filter(scope).orderBy(F.col("started_at_utc").desc()), 100, "Intentos de recuperación Silver")
        if (not rows or rows[0]["silver_run_id"] != attempt_run_id or rows[0]["status"] != "RUNNING"
                or rows[0]["silver_committed"] is not False or rows[0]["finished_at_utc"] is not None
                or (len(rows) > 1 and rows[1]["started_at_utc"] == rows[0]["started_at_utc"])):
            raise ValueError("El intento Silver cambió o no es el último RUNNING sin commit; no resolver.")
        observed = rows[0]
        scopes = spark.createDataFrame([(feed_version, sha256)], "source_feed_version string, source_sha256 string")
        states, _ = _target_states(spark, scopes, {entity: {"enabled": True}}, catalog, schema, 10)
        target = states.get((entity, feed_version, sha256), {})
        previous = [row for row in rows[1:] if row["status"] == "SUCCEEDED" and row["silver_committed"] is True
                    and target.get("run_ids") == [row["silver_run_id"]] and target.get("rows") == row["candidate_rows"]
                    and target.get("rules") == [row["silver_rule_version"]]
                    and not target.get("invalid_technical_rows") and not target.get("error")
                    and row["target_table"] == f"{catalog}.{schema}.silver_gtfs_{entity}"]
        if len(previous) != 1:
            raise ValueError("El destino no coincide con una publicación anterior única y exitosa; no resolver.")
        kind, reference = "ABANDONED", previous[0]["silver_run_id"]
        evidence = {"preserved_silver_run_id": reference, "verified_rows": target["rows"], "verified_rule": target["rules"][0]}
    stable = [layer, entity, feed_version, sha256, attempt_run_id]
    resolution = {"resolution_id": hashlib.sha256(json.dumps(stable).encode()).hexdigest(),
                  "layer": layer, "entity": entity, "source_feed_version": feed_version, "source_sha256": sha256,
                  "attempt_run_id": attempt_run_id, "observed_started_at_utc": timestamp(observed["started_at_utc"]),
                  "resolution_kind": kind, "reason": reason.strip(), "reference_run_id": reference,
                  "resolved_at_utc": datetime.now(timezone.utc), "resolved_by": "preview",
                  "evidence_json": json.dumps(evidence, sort_keys=True)}
    if mode == "apply":
        resolution["resolved_by"] = spark.sql("select current_user() as actor").first()["actor"]
        table = f"{catalog}.{schema}.audit_gtfs_attempt_resolutions"
        immutable_insert(spark, spark.createDataFrame([resolution], RESOLUTION_DDL), table,
                         ["layer", "entity", "source_feed_version", "source_sha256", "attempt_run_id"],
                         ignore=("resolved_at_utc", "resolved_by"))
    return {"persisted": mode == "apply", "resolution_id": resolution["resolution_id"], "layer": layer,
            "entity": entity, "attempt_run_id": attempt_run_id, "resolution_kind": kind, "evidence": evidence}
