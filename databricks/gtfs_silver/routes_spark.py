"""Contrato routes_v1 con expresiones Spark: sin UDFs ni collect de rutas."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING, Sequence

from .models import PreparedSnapshot, SnapshotSpec, TECHNICAL_FIELDS

if TYPE_CHECKING:
    from pyspark.sql import DataFrame

BUSINESS_TYPES = {
    "route_id": "string", "agency_id": "string", "route_short_name": "string",
    "route_long_name": "string", "route_desc": "string", "route_type": "int",
    "route_url": "string", "route_color": "string", "route_text_color": "string",
    "route_sort_order": "int",
}
REQUIRED_FIELDS = frozenset({"route_id", "agency_id", "route_type"})
RULE_VERSION = "routes_v1"
ROUTE_TYPES = (0, 1, 2, 3, 4, 5, 6, 7, 11, 12)


def validate_header(columns: Sequence[str]) -> tuple[str, ...]:
    published = tuple(columns)
    if not published or any(not isinstance(c, str) or not c.strip() for c in published):
        raise ValueError("Encabezado vacío o inválido en routes.txt.")
    if len(published) != len(set(published)):
        raise ValueError("El encabezado de routes tiene columnas duplicadas.")
    missing = REQUIRED_FIELDS - set(published)
    unknown = set(published) - set(BUSINESS_TYPES)
    if missing or unknown or not {"route_short_name", "route_long_name"} & set(published):
        raise ValueError(
            f"Revisar contrato routes: requeridas ausentes={sorted(missing)}; nuevas={sorted(unknown)}; "
            "debe publicarse al menos una columna de nombre."
        )
    return published


def read_source_header(path: str) -> tuple[str, ...]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return validate_header(next(csv.reader(handle), ()))


def read_and_validate(bronze_df: "DataFrame", published_columns: Sequence[str], spec: SnapshotSpec,
                      agency_df: "DataFrame") -> PreparedSnapshot:
    """Valida referencias del mismo snapshot y devuelve frames tipados más un resumen."""
    from pyspark.sql import functions as F, Window
    from pyspark.sql.types import StringType, TimestampType

    if spec.entity != "routes":
        raise ValueError("El contrato routes requiere un SnapshotSpec de routes.")
    columns = validate_header(published_columns)
    missing = (set(columns) | set(TECHNICAL_FIELDS)) - set(bronze_df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en Bronze routes: {sorted(missing)}")
    types = {field.name: field.dataType for field in bronze_df.schema.fields}
    if any(not isinstance(types[name], StringType) for name in (*columns, *TECHNICAL_FIELDS[:3])):
        raise ValueError("Bronze routes debe conservar campos publicados y procedencia como string.")
    if not isinstance(types["bronze_loaded_at_utc"], TimestampType):
        raise ValueError("bronze_loaded_at_utc debe ser timestamp.")
    if bronze_df.sparkSession.conf.get("spark.sql.session.timeZone") != "UTC":
        raise ValueError("Configura spark.sql.session.timeZone=UTC.")

    # La dependencia se filtra por versión Y hash antes de comprobar unicidad y unir.
    required_agency = {"agency_id", "source_feed_version", "source_sha256", "silver_rule_version"}
    if not required_agency <= set(agency_df.columns):
        raise ValueError("Falta el contrato publicado de agency en Silver.")
    agencies = agency_df.filter(
        (F.col("source_feed_version") == spec.feed_version) & (F.col("source_sha256") == spec.sha256)
    ).select("agency_id", "silver_rule_version")
    dependency = agencies.agg(
        F.count("*").alias("rows"), F.countDistinct("agency_id").alias("ids"),
        F.sum(F.when(F.col("agency_id").isNull() | F.col("agency_id").rlike(r"(?U)^\s*$")
                     | ~F.col("silver_rule_version").eqNullSafe(F.lit("agency_v1")), 1).otherwise(0)).alias("invalid"),
    ).first()
    if not dependency["rows"] or dependency["rows"] != dependency["ids"] or dependency["invalid"]:
        raise ValueError("Publica primero agency_v1 del mismo snapshot, con IDs válidos y únicos.")

    # La fuente queda como strings para detectar errores antes de convertirlos.
    selected = bronze_df.filter(F.col("source_sha256") == spec.sha256).select(
        *[F.col(name) if name in columns else F.lit(None).cast("string").alias(name)
          for name in BUSINESS_TYPES], *TECHNICAL_FIELDS,
    )
    business_json = F.to_json(F.struct(*[F.col(name) for name in columns]), {"ignoreNullFields": "false"})
    original_json = F.to_json(F.struct(*[F.col(name) for name in (*columns, *TECHNICAL_FIELDS)]),
                              {"ignoreNullFields": "false"})
    selected = selected.withColumn("_business_json", business_json).withColumn("original_row_json", original_json)
    by_id = Window.partitionBy("route_id")
    selected = (selected.withColumn("_variant_min", F.min("_business_json").over(by_id))
                .withColumn("_variant_max", F.max("_business_json").over(by_id)))
    matched_agencies = agencies.select(F.col("agency_id").alias("_matched_agency_id"))
    selected = selected.join(F.broadcast(matched_agencies),
                             selected.agency_id == matched_agencies._matched_agency_id, "left")

    def blank(name):
        return F.col(name).isNull() | F.col(name).rlike(r"(?U)^\s*$")

    errors, warnings = [], []

    def issue(condition, code, *, warning=False):
        target = warnings if warning else errors
        target.append(F.when(F.coalesce(condition, F.lit(False)), F.lit(code)))

    for field, expected in (("source_feed_version", spec.feed_version), ("source_sha256", spec.sha256),
                            ("source_file_path", spec.source_path)):
        issue(~F.col(field).eqNullSafe(F.lit(expected)), f"{field.upper()}_MISMATCH")
    issue(F.col("bronze_loaded_at_utc").isNull(), "BRONZE_TIMESTAMP_INVALID")
    for field in columns:
        issue(F.col(field).rlike(r"[\x00-\x1F\x7F]"), f"{field.upper()}_CONTROL_CHARACTER")
        if field in REQUIRED_FIELDS:
            issue(blank(field), f"{field.upper()}_MISSING")
        edge = ~blank(field) & F.col(field).rlike(r"(?U)^\s|\s$")
        issue(edge, f"{field.upper()}_EDGE_WHITESPACE", warning=field not in {"route_id", "agency_id"})
    issue(blank("route_short_name") & blank("route_long_name"), "ROUTE_NAME_MISSING")
    issue(~blank("agency_id") & F.col("_matched_agency_id").isNull(), "AGENCY_ID_NOT_FOUND")
    issue(F.col("_variant_min") != F.col("_variant_max"), "ROUTE_ID_CONFLICT")

    # try_cast evita que un valor malo aborte Spark: se conserva como rechazo explícito.
    for field in ("route_type", "route_sort_order"):
        parsed = F.expr(f"try_cast(`{field}` as int)")
        invalid = ~F.col(field).rlike(r"^[0-9]+$") | parsed.isNull()
        invalid = invalid | (~parsed.isin(*ROUTE_TYPES) if field == "route_type" else (parsed < 0))
        issue(~blank(field) & invalid, f"{field.upper()}_INVALID")
    for field in ("route_color", "route_text_color"):
        issue(~blank(field) & ~F.col(field).rlike(r"^[0-9A-Fa-f]{6}$"), f"{field.upper()}_INVALID")
    issue(~blank("route_url") & ~F.col("route_url").rlike(r"(?i)^https?://[^\s/?#]+(?:[/?#][^\s]*)?$"),
          "ROUTE_URL_INVALID")
    issue(~blank("route_desc") & ((F.col("route_desc") == F.col("route_short_name"))
                                  | (F.col("route_desc") == F.col("route_long_name"))),
          "ROUTE_DESC_REPEATS_NAME", warning=True)

    def codes(expressions):
        return F.sort_array(F.filter(F.array(*expressions), lambda value: value.isNotNull()))

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
    ).first()
    if not metrics["input_rows"]:
        raise ValueError("El snapshot de routes está vacío; revisa versión y hash.")
    summary = {key: int(value) for key, value in metrics.asDict().items()}
    summary.update(
        reconciled=summary["input_rows"] == summary["candidate_rows"] + summary["rejected_rows"]
                   + summary["identical_copies_consolidated"],
        ready_for_publication=summary["rejected_rows"] == 0, rule_version=RULE_VERSION,
    )
    expressions = []
    for field, target_type in BUSINESS_TYPES.items():
        value = F.expr(f"try_cast(`{field}` as int)") if target_type == "int" else F.col(field)
        expressions.append(F.when(blank(field), F.lit(None)).otherwise(value).cast(target_type).alias(field))
    candidates = checked.filter(candidate).select(
        *expressions, *TECHNICAL_FIELDS,
        F.array(*[F.lit(name) for name in columns]).alias("source_columns"),
        F.lit(RULE_VERSION).alias("silver_rule_version"),
    )
    rejected = checked.filter(~F.col("_is_valid")).select(
        "route_id", "source_feed_version", "source_sha256", "original_row_json", "error_codes",
        F.lit(RULE_VERSION).alias("silver_rule_version"),
    )
    warnings_frame = checked.filter(F.size("warning_codes") > 0).select("route_id", "warning_codes")
    return PreparedSnapshot({"candidates": candidates, "rejected": rejected, "warnings": warnings_frame},
                            summary, {})
