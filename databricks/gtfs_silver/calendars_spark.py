"""Calendar_v1 y calendar_dates_v1: tipos fuente, claves y contexto temporal."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from .models import PreparedSnapshot, SnapshotSpec
from .spark_validation import finish_validation, prepare_source

if TYPE_CHECKING:
    from pyspark.sql import DataFrame

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
BUSINESS_TYPES = {
    "calendar": {"service_id": "string", **{day: "int" for day in WEEKDAYS},
                 "start_date": "date", "end_date": "date"},
    "calendar_dates": {"service_id": "string", "date": "date", "exception_type": "int"},
}
KEYS = {"calendar": ("service_id",), "calendar_dates": ("service_id", "date")}


def validate_header(columns: Sequence[str], entity: str) -> tuple[str, ...]:
    if entity not in BUSINESS_TYPES:
        raise ValueError("El contrato de calendarios solo admite calendar o calendar_dates.")
    published = tuple(columns)
    if (not published or any(not isinstance(c, str) or not c.strip() for c in published)
            or len(published) != len(set(published))):
        raise ValueError(f"Encabezado vacío, inválido o repetido en {entity}.txt.")
    missing = set(BUSINESS_TYPES[entity]) - set(published)
    unknown = set(published) - set(BUSINESS_TYPES[entity])
    if missing or unknown:
        raise ValueError(f"Revisar contrato {entity}: ausentes={sorted(missing)}; nuevas={sorted(unknown)}")
    return published


def read_source_header(path: str) -> tuple[str, ...]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return validate_header(next(csv.reader(handle), ()), Path(path).stem)


def calendar_source_present(path: str) -> bool:
    """La dependencia semanal solo existe si su archivo está publicado en Staging."""
    return Path(path).with_name("calendar.txt").is_file()


def read_and_validate(
    bronze_df: "DataFrame", published_columns: Sequence[str], spec: SnapshotSpec,
    calendar_df: "DataFrame | None" = None, *, calendar_published: bool = False,
) -> PreparedSnapshot:
    from pyspark.sql import functions as F

    columns = validate_header(published_columns, spec.entity)
    if spec.entity == "calendar" and (calendar_published or calendar_df is not None):
        raise ValueError("Calendar no recibe dependencia de otro calendario.")
    if spec.entity == "calendar_dates" and calendar_published != (calendar_df is not None):
        raise ValueError("Si calendar.txt está publicado, valida contra su Silver del mismo snapshot.")
    types = BUSINESS_TYPES[spec.entity]
    selected = prepare_source(bronze_df, columns, types, KEYS[spec.entity], spec)
    errors, warnings = [], []

    def blank(field):
        return F.col(field).isNull() | F.col(field).rlike(r"(?U)^\s*$")

    def issue(condition, code, *, warning=False):
        (warnings if warning else errors).append(F.when(F.coalesce(condition, F.lit(False)), F.lit(code)))

    for field, expected in (("source_feed_version", spec.feed_version), ("source_sha256", spec.sha256),
                            ("source_file_path", spec.source_path)):
        issue(~F.col(field).eqNullSafe(F.lit(expected)), f"{field.upper()}_MISMATCH")
    issue(F.col("bronze_loaded_at_utc").isNull(), "BRONZE_TIMESTAMP_INVALID")
    for field in columns:
        issue(blank(field), f"{field.upper()}_MISSING")
        issue(F.col(field).rlike(r"[\p{Cc}]"), f"{field.upper()}_CONTROL_CHARACTER")
    issue(~blank("service_id") & F.col("service_id").rlike(r"(?U)^\s|\s$"), "SERVICE_ID_EDGE_WHITESPACE")
    issue(F.col("_variant_min") != F.col("_variant_max"), "SERVICE_KEY_CONFLICT")

    for field, target_type in types.items():
        if target_type == "date":
            # try_cast evita fallos del parser y no convierte errores a ausencias silenciosas.
            selected = selected.withColumn("_" + field, F.expr(
                f"try_cast(concat(substr(`{field}`,1,4),'-',substr(`{field}`,5,2),'-',"
                f"substr(`{field}`,7,2)) as date)"))
            parsed = F.col("_" + field)
            invalid = ~F.col(field).rlike(r"^[0-9]{8}$") | parsed.isNull() | (F.year(parsed) < 1)
            issue(~blank(field) & invalid, f"{field.upper()}_INVALID")
        elif target_type == "int":
            parsed = F.expr(f"try_cast(`{field}` as int)")
            allowed = (1, 2) if field == "exception_type" else (0, 1)
            issue(~blank(field) & (~F.col(field).rlike(r"^[0-9]+$") | parsed.isNull()
                                  | ~parsed.isin(*allowed)), f"{field.upper()}_INVALID")

    extra = {}
    if spec.entity == "calendar":
        issue(F.col("_start_date") > F.col("_end_date"), "CALENDAR_INTERVAL_REVERSED")
        wide = F.col("_end_date") > F.add_months(F.col("_start_date"), 120)
        no_weekly_service = F.lit(True)
        for day in WEEKDAYS:
            no_weekly_service = no_weekly_service & (F.expr(f"try_cast({day} as int)") == 0)
        issue(wide, "CALENDAR_INTERVAL_OVER_TEN_YEARS", warning=True)
        issue(no_weekly_service, "CALENDAR_WITHOUT_WEEKLY_SERVICE", warning=True)
        extra = {"interval_over_ten_years_rows": wide, "no_weekly_service_rows": no_weekly_service}
    else:
        different_year = F.year("_date") != int(spec.feed_version[:4])
        issue(different_year, "EXCEPTION_YEAR_DIFFERS_FROM_SNAPSHOT", warning=True)
        extra = {"different_snapshot_year_rows": different_year}
        if calendar_published:
            from pyspark.sql.types import DateType, StringType
            required = {"service_id", "start_date", "end_date", "source_feed_version",
                        "source_sha256", "silver_rule_version"}
            if not required.issubset(calendar_df.columns):
                raise ValueError("La dependencia calendar no tiene su esquema Silver.")
            schema = {f.name: f.dataType for f in calendar_df.schema.fields}
            if (any(not isinstance(schema[f], StringType) for f in
                    ("service_id", "source_feed_version", "source_sha256", "silver_rule_version"))
                    or any(not isinstance(schema[f], DateType) for f in ("start_date", "end_date"))):
                raise ValueError("La dependencia calendar requiere service_id string y fechas date.")
            dependency = calendar_df.filter((F.col("source_feed_version") == spec.feed_version)
                                             & (F.col("source_sha256") == spec.sha256))
            bad = (F.col("service_id").isNull() | F.col("service_id").rlike(r"(?U)^\s*$|^\s|\s$|[\p{Cc}]")
                   | F.col("start_date").isNull() | F.col("end_date").isNull()
                   | (F.col("start_date") > F.col("end_date"))
                   | ~F.col("silver_rule_version").eqNullSafe(F.lit("calendar_v1")))
            counts = dependency.agg(F.count("*").alias("rows"), F.countDistinct("service_id").alias("ids"),
                                    F.sum(F.when(bad, 1).otherwise(0)).alias("invalid")).first()
            if not counts["rows"] or counts["rows"] != counts["ids"] or counts["invalid"]:
                raise ValueError("Publica primero calendar_v1 del mismo snapshot, con claves y fechas válidas.")
            base = dependency.select(F.col("service_id").alias("_base_service_id"),
                                     F.col("start_date").alias("_base_start"), F.col("end_date").alias("_base_end"))
            selected = selected.join(F.broadcast(base), selected.service_id == base._base_service_id, "left")
            issue(F.col("_base_service_id").isNull(), "CALENDAR_SERVICE_ID_NOT_FOUND")
            outside = (F.col("_date") < F.col("_base_start")) | (F.col("_date") > F.col("_base_end"))
            issue(outside, "EXCEPTION_OUTSIDE_CALENDAR_INTERVAL", warning=True)
            extra["outside_calendar_interval_rows"] = outside
        else:
            issue(F.expr("try_cast(exception_type as int)") == 2,
                  "REMOVAL_WITHOUT_WEEKLY_CALENDAR", warning=True)

    expressions = [F.col("_" + field).cast(target).alias(field) if target == "date" else
                   F.expr(f"try_cast(`{field}` as {target})").alias(field)
                   for field, target in types.items()]
    result = finish_validation(selected, columns, spec, KEYS[spec.entity], spec.entity + "_v1",
                               errors, warnings, expressions, extra_metrics=extra)
    if spec.entity == "calendar_dates":
        result.summary["calendar_mode"] = "weekly_and_exceptions" if calendar_published else "dates_only"
    return result
