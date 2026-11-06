"""Adaptador PySpark de lectura para una referencia agency acotada."""

from __future__ import annotations

from typing import TYPE_CHECKING
from .agency_validation import (
    BUSINESS_FIELDS, TECHNICAL_FIELDS, SnapshotSpec, ValidationResult,
    validate_header, validate_snapshot,
)

if TYPE_CHECKING:
    from pyspark.sql import DataFrame


def read_and_validate(
    bronze_df: "DataFrame", published_columns: list[str] | tuple[str, ...],
    spec: SnapshotSpec, max_rows: int = 1000,
) -> ValidationResult:
    from pyspark.sql import functions as F
    from pyspark.sql.types import StringType, TimestampType

    published = validate_header(published_columns)
    missing = (set(published) | set(TECHNICAL_FIELDS)) - set(bronze_df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en Bronze: {sorted(missing)}")
    types = {field.name: field.dataType for field in bronze_df.schema.fields}
    if any(not isinstance(types[name], StringType) for name in published):
        raise ValueError("Las columnas publicadas de Bronze deben conservar string.")
    if any(not isinstance(types[name], StringType) for name in TECHNICAL_FIELDS[:3]):
        raise ValueError("Versión, hash y ruta Bronze deben conservar string.")
    if not isinstance(types["bronze_loaded_at_utc"], TimestampType):
        raise ValueError("bronze_loaded_at_utc debe ser timestamp.")
    if bronze_df.sparkSession.conf.get("spark.sql.session.timeZone") != "UTC":
        raise ValueError("Configura spark.sql.session.timeZone=UTC antes de leer timestamps.")

    # Filtrar por hash permite detectar versiones o rutas inconsistentes sin ocultarlas.
    selected = bronze_df.filter(F.col("source_sha256") == spec.sha256)
    expressions = [
        F.col(name) if name in published else F.lit(None).cast("string").alias(name)
        for name in BUSINESS_FIELDS
    ] + [F.col(name) for name in TECHNICAL_FIELDS]
    rows = selected.select(*expressions).limit(max_rows + 1).collect()
    return validate_snapshot([row.asDict() for row in rows], published, spec, max_rows)


def result_frames(spark, result: ValidationResult) -> dict[str, "DataFrame"]:
    """Esquemas explícitos incluso cuando no hay rechazos ni advertencias."""
    from pyspark.sql.types import (
        ArrayType, StringType, StructField, StructType, TimestampType,
    )

    candidate_schema = StructType(
        [StructField(name, StringType(), True) for name in BUSINESS_FIELDS]
        + [StructField(name, StringType(), False) for name in TECHNICAL_FIELDS[:3]]
        + [StructField("bronze_loaded_at_utc", TimestampType(), False),
           StructField("source_columns", ArrayType(StringType(), False), False),
           StructField("silver_rule_version", StringType(), False)]
    )
    rejected_schema = StructType([
        StructField("agency_id", StringType(), True),
        StructField("source_feed_version", StringType(), True),
        StructField("source_sha256", StringType(), True),
        StructField("original_row_json", StringType(), False),
        StructField("error_codes", ArrayType(StringType(), False), False),
        StructField("silver_rule_version", StringType(), False),
    ])
    warning_schema = StructType([
        StructField("agency_id", StringType(), True),
        StructField("warning_codes", ArrayType(StringType(), False), False),
    ])
    return {
        "candidates": spark.createDataFrame(result.candidates, candidate_schema),
        "rejected": spark.createDataFrame(result.rejected, rejected_schema),
        "warnings": spark.createDataFrame(result.warnings, warning_schema),
    }
