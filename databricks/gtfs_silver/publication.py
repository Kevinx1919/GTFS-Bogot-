"""Publicación Delta de un snapshot validado, con auditoría y cuarentena."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from typing import Any
from uuid import uuid4

from .agency_validation import SnapshotSpec, ValidationResult
from .agency_spark import result_frames
from .models import PreparedSnapshot


class SnapshotRejectedError(RuntimeError):
    """El snapshot tiene rechazos y no se modifica su tabla Silver."""


def simple_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Identificador no permitido: {value!r}")
    return value


def quoted_table(value: str) -> str:
    parts = value.split(".")
    if len(parts) != 3:
        raise ValueError("La tabla debe indicar catálogo, schema y nombre.")
    return ".".join(f"`{simple_identifier(part)}`" for part in parts)


@dataclass(frozen=True)
class PublicationTables:
    catalog: str
    schema: str
    entity: str = "agency"

    def __post_init__(self) -> None:
        for value in (self.catalog, self.schema, self.entity):
            simple_identifier(value)

    def name(self, kind: str) -> str:
        names = {
            "silver": f"silver_gtfs_{self.entity}",
            "quarantine": f"quarantine_gtfs_{self.entity}",
            "audit": "audit_gtfs_silver_runs",
        }
        return f"{self.catalog}.{self.schema}.{names[kind]}"


def snapshot_predicate(spec: SnapshotSpec) -> str:
    return f"source_feed_version = '{spec.feed_version}' and source_sha256 = '{spec.sha256}'"


def _overwrite_scope(frame, table: str, predicate: str, *, allow_empty: bool = False) -> None:
    """Un único commit Delta sustituye el ámbito; nunca toda la tabla existente."""
    spark = frame.sparkSession
    quoted = quoted_table(table)
    # Una agregación comprueba vacío y ámbito en lugar de dos acciones independientes.
    from pyspark.sql import functions as F
    condition = F.expr(predicate)
    checks = frame.agg(F.count("*").alias("rows"),
                       F.max(F.when(condition.isNull() | ~condition, 1).otherwise(0)).alias("outside")).first()
    if not allow_empty and not checks["rows"]:
        raise ValueError("La salida está vacía; bloqueo la escritura.")
    if checks["outside"]:
        raise ValueError("Hay filas fuera del snapshot o ejecución seleccionados.")
    if spark.catalog.tableExists(quoted):
        details = spark.sql(f"describe detail {quoted}").first()
        if details["format"] != "delta":
            raise ValueError("La tabla destino debe ser Delta.")
        current = [(f.name, f.dataType.simpleString()) for f in spark.table(quoted).schema.fields]
        proposed = [(f.name, f.dataType.simpleString()) for f in frame.schema.fields]
        if current != proposed:
            raise ValueError("Cambió el esquema destino; requiere una migración explícita.")
        (frame.write.format("delta").mode("overwrite")
         .option("replaceWhere", predicate).saveAsTable(quoted))
    else:
        # Si otro escritor crea la tabla, falla en lugar de reemplazarla.
        frame.writeTo(quoted).using("delta").create()


def _versioned_table(spark, table: str):
    """Recibe catálogo.schema.tabla sin comillas y fija una versión Delta para su lectura."""
    quoted = quoted_table(table)
    version = spark.sql(f"describe history {quoted} limit 1").first()["version"]
    return spark.read.option("versionAsOf", version).table(quoted)


def _same_rows(left, right) -> bool:
    return not left.exceptAll(right).unionByName(right.exceptAll(left)).limit(1).count()


def _check_result(result: ValidationResult) -> None:
    summary = result.summary
    expected = len(result.candidates) + len(result.rejected) + summary["identical_copies_consolidated"]
    if (summary["input_rows"] < 1 or not summary["reconciled"]
            or summary["input_rows"] != expected
            or summary["candidate_rows"] != len(result.candidates)
            or summary["rejected_rows"] != len(result.rejected)
            or summary["ready_for_publication"] != (len(result.rejected) == 0)):
        raise ValueError("El resultado no reconcilia; no publicar.")
    if summary["identical_copies_consolidated"] < 0:
        raise ValueError("El conteo de copias consolidadas no puede ser negativo.")


def _audit(spark, tables: PublicationTables, spec: SnapshotSpec, result: ValidationResult | PreparedSnapshot,
           run_id: str, status: str, started: datetime, committed: bool, error: str | None = None) -> None:
    from pyspark.sql.types import (
        BooleanType, LongType, StringType, StructField, StructType, TimestampType,
    )
    fields = [
        *[(name, StringType()) for name in (
            "entity", "source_feed_version", "source_sha256", "silver_run_id",
            "status", "silver_rule_version", "target_table", "reference_versions_json",
        )],
        *[(name, LongType()) for name in (
            "input_rows", "candidate_rows", "rejected_rows", "identical_copies_consolidated", "warning_rows",
        )],
        ("started_at_utc", TimestampType()), ("finished_at_utc", TimestampType()),
        ("silver_committed", BooleanType()), ("error_message", StringType()),
    ]
    row = {
        "entity": tables.entity, "source_feed_version": spec.feed_version,
        "source_sha256": spec.sha256, "silver_run_id": run_id, "status": status,
        "silver_rule_version": result.summary["rule_version"], "target_table": tables.name("silver"),
        "reference_versions_json": json.dumps(result.reference_versions, sort_keys=True),
        **{key: result.summary[key] for key in (
            "input_rows", "candidate_rows", "rejected_rows", "identical_copies_consolidated", "warning_rows",
        )},
        "started_at_utc": started,
        "finished_at_utc": None if status == "RUNNING" else datetime.now(timezone.utc),
        "silver_committed": committed, "error_message": error,
    }
    schema = StructType([StructField(name, data_type, True) for name, data_type in fields])
    frame = spark.createDataFrame([row], schema)
    scope = snapshot_predicate(spec) + f" and entity = '{tables.entity}' and silver_run_id = '{run_id}'"
    _overwrite_scope(frame, tables.name("audit"), scope)


def publish_agency(
    spark, result: ValidationResult, spec: SnapshotSpec, tables: PublicationTables,
    *, run_id: str | None = None, mode: str = "publish", verify_history: bool = True,
) -> dict[str, Any]:
    """Compatibilidad con agency_v1; la escritura común se ejecuta una sola vez."""
    if tables.entity != "agency":
        raise ValueError("Este adaptador solo acepta agency.")
    _check_result(result)
    frames = {} if mode == "validate" else result_frames(spark, result)
    prepared = PreparedSnapshot(frames, result.summary, result.reference_versions)
    return publish_snapshot(spark, prepared, spec, tables, run_id=run_id,
                            mode=mode, verify_history=verify_history)


def publish_snapshot(
    spark, result: PreparedSnapshot, spec: SnapshotSpec, tables: PublicationTables,
    *, run_id: str | None = None, mode: str = "publish", verify_history: bool = True,
) -> dict[str, Any]:
    """Un escritor para contratos ya validados; conserva esquemas y ámbito por snapshot."""
    from pyspark.sql import functions as F

    identifiers = {"agency": "agency_id", "routes": "route_id"}
    if tables.entity not in identifiers or spec.entity != tables.entity:
        raise ValueError("La entidad publicada debe coincidir con su contrato y snapshot.")
    identifier = identifiers[tables.entity]
    if mode not in {"validate", "publish"}:
        raise ValueError("mode debe ser validate o publish.")
    summary = result.summary
    counts = ("input_rows", "candidate_rows", "rejected_rows", "identical_copies_consolidated", "warning_rows")
    if (any(type(summary.get(key)) is not int or summary[key] < 0 for key in counts)
            or summary["input_rows"] < 1 or not summary["reconciled"]
            or summary["input_rows"] != sum(summary[key] for key in counts[1:4])
            or summary["ready_for_publication"] != (summary["rejected_rows"] == 0)):
        raise ValueError("El resultado no reconcilia; no publicar.")
    if mode == "validate":
        return {"status": "VALIDATED" if result.summary["ready_for_publication"] else "REJECTED",
                "persisted": False, **result.summary}
    run_id = run_id or str(uuid4())
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", run_id):
        raise ValueError("run_id inválido.")
    if spark.conf.get("spark.sql.session.timeZone") != "UTC":
        raise ValueError("La sesión debe usar UTC.")
    started = datetime.now(timezone.utc)
    scope = snapshot_predicate(spec)
    committed = False
    _audit(spark, tables, spec, result, run_id, "RUNNING", started, committed)
    try:
        frames = result.frames
        # La cuarentena agrupa copias del mismo rechazo y conserva su multiplicidad.
        quarantine = (
            frames["rejected"].groupBy(identifier, "original_row_json", "error_codes", "silver_rule_version")
            .count().withColumnRenamed("count", "input_copies")
            .withColumn("record_hash", F.sha2(F.concat("original_row_json", F.to_json("error_codes")), 256))
            .withColumn("entity", F.lit(tables.entity))
            .withColumn("source_feed_version", F.lit(spec.feed_version))
            .withColumn("source_sha256", F.lit(spec.sha256))
            .withColumn("silver_run_id", F.lit(run_id))
            .withColumn("quarantined_at_utc", F.lit(started))
        )
        run_scope = scope + f" and entity = '{tables.entity}' and silver_run_id = '{run_id}'"
        _overwrite_scope(quarantine, tables.name("quarantine"), run_scope, allow_empty=True)
        if not result.summary["ready_for_publication"]:
            raise SnapshotRejectedError("Snapshot rechazado: consulta cuarentena y auditoría.")
        output = (
            frames["candidates"]
            .withColumn("silver_run_id", F.lit(run_id))
            .withColumn("silver_loaded_at_utc", F.lit(started))
        )
        checks = output.agg(
            F.count("*").alias("rows"), F.countDistinct(identifier).alias("ids"),
            F.max(F.when(F.col(identifier).isNull() | F.col(identifier).rlike(r"(?U)^\s*$"), 1)
                  .otherwise(0)).alias("blank"),
        ).first()
        if checks["blank"] or checks["rows"] != checks["ids"] or checks["rows"] != summary["candidate_rows"]:
            raise ValueError("No publicar IDs vacíos, repetidos o conteos inconsistentes.")
        target = tables.name("silver")
        previous_others = None
        if verify_history and spark.catalog.tableExists(quoted_table(target)):
            previous_others = _versioned_table(spark, target).filter(f"not ({scope})")
        _overwrite_scope(output, target, scope)
        committed = True
        observed = _versioned_table(spark, target)
        if not _same_rows(output, observed.filter(scope).select(*output.columns)):
            raise RuntimeError("La lectura posterior no coincide con los candidatos.")
        if previous_others is not None and not _same_rows(previous_others, observed.filter(f"not ({scope})")):
            raise RuntimeError("Otra versión cambió durante la ejecución; revisar concurrencia.")
        _audit(spark, tables, spec, result, run_id, "SUCCEEDED", started, committed)
        return {"status": "SUCCEEDED", "persisted": True, "silver_run_id": run_id,
                "table": target, "history_checked": verify_history, **result.summary}
    except Exception as error:
        status = "REJECTED" if isinstance(error, SnapshotRejectedError) else "FAILED"
        try:
            _audit(spark, tables, spec, result, run_id, status, started, committed, str(error)[:1000])
        except Exception as audit_error:
            raise RuntimeError(
                f"Falló la ejecución y su auditoría; silver_committed={committed}. "
                "Revisa el Job antes de reintentar."
            ) from audit_error
        raise
