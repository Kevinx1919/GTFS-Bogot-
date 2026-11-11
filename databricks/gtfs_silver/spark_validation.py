"""Mecánica compartida de contratos Spark; las reglas de negocio viven en cada entidad."""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping, Sequence

from .models import PreparedSnapshot, SnapshotSpec, TECHNICAL_FIELDS

if TYPE_CHECKING:
    from pyspark.sql import Column, DataFrame


def prepare_source(
    bronze_df: "DataFrame", published: Sequence[str], business_types: Mapping[str, str],
    identifier: str, spec: SnapshotSpec,
) -> "DataFrame":
    """Comprueba tipos Bronze y conserva huellas fuente antes de normalizar."""
    from pyspark.sql import functions as F, Window
    from pyspark.sql.types import StringType, TimestampType

    missing = (set(published) | set(TECHNICAL_FIELDS)) - set(bronze_df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en Bronze {spec.entity}: {sorted(missing)}")
    types = {field.name: field.dataType for field in bronze_df.schema.fields}
    if any(not isinstance(types[name], StringType) for name in (*published, *TECHNICAL_FIELDS[:3])):
        raise ValueError("Bronze debe conservar campos publicados y procedencia como string.")
    if not isinstance(types["bronze_loaded_at_utc"], TimestampType):
        raise ValueError("bronze_loaded_at_utc debe ser timestamp.")
    if bronze_df.sparkSession.conf.get("spark.sql.session.timeZone") != "UTC":
        raise ValueError("Configura spark.sql.session.timeZone=UTC.")
    selected = bronze_df.filter(F.col("source_sha256") == spec.sha256).select(
        *[F.col(name) if name in published else F.lit(None).cast("string").alias(name)
          for name in business_types], *TECHNICAL_FIELDS,
    )
    selected = selected.withColumn(
        "_business_json", F.to_json(F.struct(*[F.col(name) for name in published]),
                                    {"ignoreNullFields": "false"}),
    ).withColumn(
        "original_row_json", F.to_json(F.struct(*[F.col(name) for name in (*published, *TECHNICAL_FIELDS)]),
                                       {"ignoreNullFields": "false"}),
    )
    by_id = Window.partitionBy(identifier)
    return (selected.withColumn("_variant_min", F.min("_business_json").over(by_id))
            .withColumn("_variant_max", F.max("_business_json").over(by_id)))


def finish_validation(
    selected: "DataFrame", published: Sequence[str], spec: SnapshotSpec,
    identifier: str, rule_version: str, errors: Sequence["Column"], warnings: Sequence["Column"],
    expressions: Sequence["Column"], *, extra_metrics: Mapping[str, "Column"] | None = None,
) -> PreparedSnapshot:
    """Reconcilia entradas y copias sin traer registros de negocio al driver."""
    from pyspark.sql import functions as F, Window

    def codes(items: Sequence["Column"]) -> "Column":
        return F.sort_array(F.filter(F.array(*items).cast("array<string>"), lambda value: value.isNotNull()))

    checked = selected.withColumn("error_codes", codes(errors)).withColumn("warning_codes", codes(warnings))
    checked = checked.withColumn("_is_valid", F.size("error_codes") == 0)
    copies = Window.partitionBy("_business_json", "_is_valid").orderBy(
        F.col("bronze_loaded_at_utc").asc_nulls_first(), "original_row_json",
    )
    checked = checked.withColumn("_copy_rank", F.row_number().over(copies))
    candidate = F.col("_is_valid") & (F.col("_copy_rank") == 1)
    metrics = checked.agg(
        F.count("*").alias("input_rows"),
        F.sum(F.when(candidate, 1).otherwise(0)).alias("candidate_rows"),
        F.sum(F.when(~F.col("_is_valid"), 1).otherwise(0)).alias("rejected_rows"),
        F.sum(F.when(F.col("_is_valid") & (F.col("_copy_rank") > 1), 1).otherwise(0))
         .alias("identical_copies_consolidated"),
        F.sum(F.when(F.size("warning_codes") > 0, 1).otherwise(0)).alias("warning_rows"),
        *[F.sum(F.when(candidate & condition, 1).otherwise(0)).alias(name)
          for name, condition in (extra_metrics or {}).items()],
    ).first()
    if not metrics["input_rows"]:
        raise ValueError(f"El snapshot de {spec.entity} está vacío; revisa versión y hash.")
    summary = {key: int(value) for key, value in metrics.asDict().items()}
    summary.update(
        reconciled=summary["input_rows"] == summary["candidate_rows"] + summary["rejected_rows"]
                   + summary["identical_copies_consolidated"],
        ready_for_publication=summary["rejected_rows"] == 0, rule_version=rule_version,
    )
    candidates = checked.filter(candidate).select(
        *expressions, *TECHNICAL_FIELDS,
        F.array(*[F.lit(name) for name in published]).alias("source_columns"),
        F.lit(rule_version).alias("silver_rule_version"),
    )
    rejected = checked.filter(~F.col("_is_valid")).select(
        identifier, "source_feed_version", "source_sha256", "original_row_json", "error_codes",
        F.lit(rule_version).alias("silver_rule_version"),
    )
    warning_frame = checked.filter(F.size("warning_codes") > 0).select(identifier, "warning_codes")
    return PreparedSnapshot({"candidates": candidates, "rejected": rejected, "warnings": warning_frame},
                            summary, {})
