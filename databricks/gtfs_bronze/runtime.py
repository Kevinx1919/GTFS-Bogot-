"""IO explícito para Bronze; las funciones Spark importan sus dependencias al ejecutarse."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import time
from uuid import uuid4
from typing import TYPE_CHECKING, Any, BinaryIO, Callable
from zipfile import ZipFile, ZipInfo

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession

from .contracts import CHECK_FIELDS, RULE_VERSION, canonical_json, load_decision, quoted_table

TECHNICAL_COLUMNS = {"source_feed_version", "source_sha256", "source_file_path", "bronze_loaded_at_utc"}
CLOSURE_DDL = """
quality_run_id string, event_type string, source_feed_version string, source_sha256 string,
rule_version string, started_at_utc timestamp, completed_at_utc timestamp,
status string, total_checks bigint, blocking_failures bigint, warning_count bigint,
validation_completed boolean, ready_for_silver boolean, warning_policy string,
entity_inventory_json string, result_sha256 string, coordinator_run_id string
"""


def stream_sha256(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def file_sha256(path: str) -> str:
    with Path(path).open("rb") as stream:
        return stream_sha256(stream)


def preserve_raw(path: str, content: bytes, expected_hash: str) -> bool:
    """Reutiliza solo contenido íntegro; jamás repara Raw sobrescribiéndolo."""
    if hashlib.sha256(content).hexdigest() != expected_hash:
        raise RuntimeError("El payload no coincide con su SHA-256; Raw bloqueado.")
    destination = Path(path)
    reused = destination.exists()
    if not reused:
        try:
            with destination.open("xb") as stream:
                stream.write(content)
        except FileExistsError:
            reused = True
    if file_sha256(path) != expected_hash:
        raise RuntimeError("El ZIP Raw existente no coincide con su hash. No se sobrescribe; revisa su recuperación.")
    return reused


def extract_verified(archive: ZipFile, member: ZipInfo, destination: str) -> bool:
    """Compara cada TXT reutilizado con el miembro exacto del ZIP Raw."""
    target = Path(destination)
    reused = target.exists()
    if not reused:
        with archive.open(member) as source, target.open("xb") as output:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                output.write(chunk)
    else:
        with archive.open(member) as source:
            expected = stream_sha256(source)
        if file_sha256(destination) != expected:
            raise RuntimeError(f"Staging inconsistente: {target.name}. Reconstruye esta copia derivada; Raw permanece intacto.")
    return reused


def download_response(
    url: str, http_get: Callable[..., Any], *, sleep: Callable[[float], None] = time.sleep,
    max_attempts: int = 3, retry_errors: tuple[type[Exception], ...] = (ConnectionError, TimeoutError),
) -> Any:
    """Reintenta únicamente red, 429 y errores temporales del proveedor."""
    if max_attempts < 1:
        raise ValueError("max_attempts debe ser positivo.")
    for attempt in range(max_attempts):
        try:
            response = http_get(url, headers={"User-Agent": "bogota-gtfs-mobility-lakehouse/0.1"}, timeout=(10, 120))
            if response.status_code in {429, 500, 502, 503, 504} and attempt + 1 < max_attempts:
                response.close()
                sleep(2 ** attempt)
                continue
            response.raise_for_status()
            return response
        except retry_errors:
            if attempt + 1 == max_attempts:
                raise
            sleep(2 ** attempt)
    raise RuntimeError("Descarga sin resultado.")


def read_gtfs_header(source_path: str) -> list[str]:
    with open(source_path, "r", encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream), None)
    if not header or any(not column.strip() for column in header) or len(header) != len(set(header)):
        raise RuntimeError(f"Encabezado vacío, inválido o duplicado: {source_path}.")
    if TECHNICAL_COLUMNS & set(header):
        raise RuntimeError("El proveedor publicó nombres reservados para procedencia técnica.")
    return header


def source_frame(spark: SparkSession, path: str, columns: list[str]) -> DataFrame:
    from pyspark.sql.types import StringType, StructField, StructType
    schema = StructType([StructField(column, StringType(), True) for column in columns])
    return (spark.read.schema(schema).option("header", True).option("enforceSchema", False)
            .option("mode", "FAILFAST").csv(path))


def pinned_table(spark: SparkSession, table: str) -> tuple[DataFrame, int]:
    quoted = quoted_table(table)
    version = int(spark.sql(f"describe history {quoted} limit 1").first()["version"])
    return spark.read.option("versionAsOf", version).table(quoted), version


def snapshot_metrics(frame: DataFrame, feed_version: str, sha256: str) -> tuple[int, int]:
    from pyspark.sql import functions as F
    row = (frame.filter(F.col("source_sha256") == sha256).agg(
        F.count("*").alias("rows"),
        F.count(F.when(F.col("source_feed_version").isNull() | (F.col("source_feed_version") != feed_version), 1)).alias("wrong_version"),
    ).first())
    return int(row["rows"]), int(row["wrong_version"])


def load_frame(spark: SparkSession, source: DataFrame, *, table: str, source_path: str, feed_version: str, sha256: str) -> tuple[int, bool]:
    """Carga append-only bajo un único escritor; detecta evidencia parcial antes de añadir filas."""
    from pyspark.sql import functions as F
    quoted = quoted_table(table)
    source_count = source.count()
    loaded_count, wrong = 0, 0
    if spark.catalog.tableExists(quoted):
        previous, _ = pinned_table(spark, table)
        loaded_count, wrong = snapshot_metrics(previous, feed_version, sha256)
    reused = load_decision(source_count, loaded_count, wrong)
    if not reused:
        bronze = (source.withColumn("source_feed_version", F.lit(feed_version))
                  .withColumn("source_sha256", F.lit(sha256))
                  .withColumn("source_file_path", F.lit(source_path))
                  .withColumn("bronze_loaded_at_utc", F.current_timestamp()))
        (bronze.write.format("delta").mode("append").option("mergeSchema", "true")
         .option("txnAppId", f"gtfs_bronze:{table}:{sha256}").option("txnVersion", 0).saveAsTable(quoted))
        current, _ = pinned_table(spark, table)
        count, wrong = snapshot_metrics(current, feed_version, sha256)
        load_decision(source_count, count, wrong)
        if count != source_count:
            raise RuntimeError("No se confirmó la carga Bronze; no promover a Silver.")
    return source_count, reused


def immutable_insert(spark: SparkSession, frame: DataFrame, table: str, keys: list[str], *, ignore: tuple[str, ...] = ()) -> None:
    """Inserta evidencia faltante; rechaza cambios bajo la misma clave de evaluación."""
    quoted = quoted_table(table)
    fields = frame.schema.fields
    # Todos estos nombres proceden de esquemas internos, no del proveedor.
    import re
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field.name) for field in fields):
        raise ValueError("Columna de auditoría no permitida.")
    ddl = ", ".join(f"`{field.name}` {field.dataType.simpleString()}" for field in fields)
    spark.sql(f"create table if not exists {quoted} ({ddl}) using delta")
    current = spark.table(quoted)
    if [(f.name, f.dataType.simpleString()) for f in current.schema.fields] != [(f.name, f.dataType.simpleString()) for f in fields]:
        raise RuntimeError(f"El esquema de {table} requiere una migración explícita.")
    columns = [field.name for field in fields if field.name not in ignore]
    existing = current.join(frame.select(*keys).distinct(), keys, "inner")
    proposed = frame.select(*columns).distinct()
    if existing.select(*columns).distinct().exceptAll(proposed).limit(1).count():
        raise RuntimeError("La evaluación persistida tiene otro resultado. Reinicia desde el bloque 1.")
    view = "bronze_audit_" + uuid4().hex
    frame.createOrReplaceTempView(view)
    predicate = " and ".join(f"target.`{key}` = source.`{key}`" for key in keys)
    try:
        spark.sql(f"merge into {quoted} as target using `{view}` as source on {predicate} when not matched then insert *")
    finally:
        spark.catalog.dropTempView(view)
    persisted = spark.table(quoted).join(frame.select(*keys).distinct(), keys, "inner").select(*columns).distinct()
    if proposed.exceptAll(persisted).unionByName(persisted.exceptAll(proposed)).limit(1).count():
        raise RuntimeError("La auditoría no coincide después de persistir; no continuar.")


def persist_closure(spark: SparkSession, checks: list[tuple], summary: dict, *, quality_table: str, closure_table: str) -> None:
    from pyspark.sql.types import StructType, StructField, StringType, TimestampType
    check_schema = StructType([StructField(name, TimestampType() if name == "checked_at_utc" else StringType(), False) for name in CHECK_FIELDS])
    immutable_insert(spark, spark.createDataFrame(checks, check_schema), quality_table,
                     ["quality_run_id", "check_name", "entity_name", "severity"])
    # El cierre se escribe después de todos los checks; no existe una transacción entre ambas tablas.
    frame = spark.createDataFrame([summary], CLOSURE_DDL)
    immutable_insert(spark, frame, closure_table, ["quality_run_id", "event_type"], ignore=("completed_at_utc",))


def publish_task_values(dbutils: Any, values: dict, *, required: bool = False) -> None:
    try:
        for key, value in values.items():
            dbutils.jobs.taskValues.set(key=key, value=value)
    except Exception as error:
        if required:
            raise RuntimeError("No se entregaron task values al Job; revisa sus parámetros antes de continuar.") from error
        print(f"Task values no disponibles en esta ejecución interactiva: {type(error).__name__}.")


def start_validation(spark: SparkSession, *, closure_table: str, run_id: str, feed_version: str, sha256: str, started_at: datetime, coordinator_run_id: str = "") -> None:
    """Hace visible una evaluación incompleta para no reutilizar un éxito anterior."""
    summary = {
        "quality_run_id": run_id, "event_type": "STARTED", "source_feed_version": feed_version,
        "source_sha256": sha256, "rule_version": RULE_VERSION, "started_at_utc": started_at,
        "completed_at_utc": None, "status": "RUNNING", "total_checks": 0,
        "blocking_failures": 0, "warning_count": 0, "validation_completed": False,
        "ready_for_silver": False, "warning_policy": "silver_contracts_v1",
        "entity_inventory_json": "{}", "coordinator_run_id": coordinator_run_id,
        "result_sha256": hashlib.sha256(canonical_json([run_id, feed_version, sha256, RULE_VERSION]).encode()).hexdigest(),
    }
    immutable_insert(spark, spark.createDataFrame([summary], CLOSURE_DDL), closure_table,
                     ["quality_run_id", "event_type"])
