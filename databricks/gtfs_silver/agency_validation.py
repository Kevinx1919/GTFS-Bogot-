"""Validación de agency en memoria; no contiene escrituras ni acceso de red."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from importlib import metadata, resources
import csv
import json
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from .models import SnapshotSpec, TECHNICAL_FIELDS

BUSINESS_FIELDS = (
    "agency_id", "agency_name", "agency_url", "agency_timezone",
    "agency_lang", "agency_phone", "agency_fare_url", "agency_email",
)
REQUIRED_FIELDS = frozenset(BUSINESS_FIELDS[:4])
REFERENCE_VERSIONS = {"langcodes": "3.5.1", "tzdata": "2026.6"}
RULE_VERSION = "agency_v1"


@dataclass
class ValidationResult:
    candidates: list[dict[str, Any]]
    rejected: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    summary: dict[str, Any]
    reference_versions: dict[str, str]


def is_blank(value: Any) -> bool:
    return value is None or isinstance(value, str) and not value.strip()


def has_controls(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def valid_url(value: str) -> bool:
    """Control estructural HTTP(S), sin consultas de disponibilidad."""
    if not isinstance(value, str) or any(c.isspace() for c in value) or has_controls(value):
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        parsed.port  # Fuerza la comprobación de puertos y corchetes malformados.
        return parsed.scheme.lower() in {"http", "https"} and bool(host)
    except (ValueError, UnicodeError):
        return False


@lru_cache(maxsize=1)
def reference_versions() -> dict[str, str]:
    """Bloquea dependencias distintas para no aprobar con otra referencia sin revisión."""
    actual = {}
    for package, expected in REFERENCE_VERSIONS.items():
        try:
            actual[package] = metadata.version(package)
        except metadata.PackageNotFoundError as error:
            raise RuntimeError(
                "Faltan validadores. Instala databricks/requirements-silver.txt "
                "y reinicia desde el bloque 1."
            ) from error
        if actual[package] != expected:
            raise RuntimeError(
                f"{package}: se requiere {expected}; está instalada {actual[package]}. "
                "Usa requirements-silver.txt o revisa la versión del contrato."
            )
    return actual


@lru_cache(maxsize=1)
def known_timezones() -> frozenset[str]:
    # La lista proviene del paquete fijado, no de una base del sistema operativo.
    reference_versions()
    return frozenset(resources.files("tzdata").joinpath("zones").read_text("utf-8").splitlines())


def valid_language(value: str) -> bool:
    reference_versions()
    if not re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", value):
        return False
    from langcodes import tag_is_valid
    try:
        return bool(tag_is_valid(value))
    except ValueError:
        return False


def validate_header(columns: Sequence[str]) -> tuple[str, ...]:
    """Falla antes de evaluar filas si cambió el contrato publicado."""
    published = tuple(columns)
    if not published or any(not isinstance(c, str) or not c.strip() for c in published):
        raise ValueError("Encabezado vacío o inválido: revisa agency.txt en Staging.")
    if len(published) != len(set(published)):
        raise ValueError("El encabezado tiene columnas duplicadas.")
    missing = REQUIRED_FIELDS - set(published)
    unknown = set(published) - set(BUSINESS_FIELDS)
    if missing or unknown:
        raise ValueError(f"Revisar contrato: requeridas ausentes={sorted(missing)}; nuevas={sorted(unknown)}.")
    return published


def read_source_header(path: str) -> tuple[str, ...]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return validate_header(next(csv.reader(handle), ()))


def source_json(row: Mapping[str, Any]) -> str:
    return json.dumps(dict(row), ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))


def _utc_stamp(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _row_issues(
    row: Mapping[str, Any], columns: Sequence[str], spec: SnapshotSpec,
) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    expected = {
        "source_feed_version": spec.feed_version,
        "source_sha256": spec.sha256,
        "source_file_path": spec.source_path,
    }
    for field, value in expected.items():
        if row.get(field) != value:
            errors.append(f"{field.upper()}_MISMATCH")
    if _utc_stamp(row.get("bronze_loaded_at_utc")) is None:
        errors.append("BRONZE_TIMESTAMP_INVALID")

    for field in columns:
        value = row.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"{field.upper()}_TYPE_INVALID")
            continue
        if isinstance(value, str) and has_controls(value):
            errors.append(f"{field.upper()}_CONTROL_CHARACTER")
        if is_blank(value):
            if field in REQUIRED_FIELDS:
                errors.append(f"{field.upper()}_MISSING")
            continue
        if value != value.strip():
            if field == "agency_id":
                errors.append("AGENCY_ID_EDGE_WHITESPACE")
            else:
                warnings.append(f"{field.upper()}_EDGE_WHITESPACE")
        if field in {"agency_url", "agency_fare_url"} and not valid_url(value):
            errors.append(f"{field.upper()}_FORMAT_INVALID")
        if field == "agency_timezone" and value not in known_timezones():
            errors.append("AGENCY_TIMEZONE_UNKNOWN")
        if field == "agency_lang" and not valid_language(value):
            errors.append("AGENCY_LANG_INVALID")
        if field == "agency_email" and not re.fullmatch(r"[^@\s]+@[^@\s]+", value):
            errors.append("AGENCY_EMAIL_FORMAT_INVALID")
    return errors, warnings


def validate_snapshot(
    rows: Sequence[Mapping[str, Any]],
    published_columns: Sequence[str],
    spec: SnapshotSpec,
    max_rows: int = 1000,
) -> ValidationResult:
    """Valida una referencia pequeña y acotada; no se usa para trips o stop_times."""
    columns = validate_header(published_columns)
    if max_rows < 1 or not rows or len(rows) > max_rows:
        raise ValueError(f"Se requieren entre 1 y {max_rows} filas de agency; revisa la selección.")
    versions = dict(reference_versions())

    # Comparar únicamente negocio evita que un timestamp oculte copias idénticas.
    variants: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        identifier = row.get("agency_id")
        if isinstance(identifier, str) and not is_blank(identifier):
            variants[identifier].add(source_json({field: row.get(field) for field in columns}))
    conflicts = {identifier for identifier, values in variants.items() if len(values) > 1}
    zones = {row.get("agency_timezone") for row in rows if isinstance(row.get("agency_timezone"), str)
             and not is_blank(row.get("agency_timezone"))}
    inconsistent_zone = len(zones) > 1

    rejected, warnings = [], []
    valid_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source_row in rows:
        row = dict(source_row)
        errors, row_warnings = _row_issues(row, columns, spec)
        if row.get("agency_id") in conflicts:
            errors.append("AGENCY_ID_CONFLICT")
        if inconsistent_zone:
            errors.append("SNAPSHOT_TIMEZONE_INCONSISTENT")
        if row_warnings:
            warnings.append({"agency_id": row.get("agency_id"), "warning_codes": sorted(set(row_warnings))})
        if errors:
            rejected.append({
                "agency_id": row.get("agency_id"),
                "source_feed_version": row.get("source_feed_version"),
                "source_sha256": row.get("source_sha256"),
                "original_row_json": source_json(row),
                "error_codes": sorted(set(errors)),
                "silver_rule_version": RULE_VERSION,
            })
            continue
        key = source_json({field: row.get(field) for field in columns})
        valid_groups[key].append(row)

    candidates, copies = [], 0
    for group in valid_groups.values():
        chosen = min(group, key=lambda row: _utc_stamp(row["bronze_loaded_at_utc"]))
        candidate = {field: (None if field not in columns or is_blank(chosen.get(field))
                             else chosen[field]) for field in BUSINESS_FIELDS}
        candidate.update({field: chosen[field] for field in TECHNICAL_FIELDS})
        candidate["bronze_loaded_at_utc"] = _utc_stamp(chosen["bronze_loaded_at_utc"])
        candidate["source_columns"] = list(columns)
        candidate["silver_rule_version"] = RULE_VERSION
        candidates.append(candidate)
        copies += len(group) - 1

    candidates.sort(key=lambda row: row["agency_id"])
    rejected.sort(key=lambda row: row["original_row_json"])
    summary = {
        "input_rows": len(rows), "candidate_rows": len(candidates),
        "rejected_rows": len(rejected), "identical_copies_consolidated": copies,
        "warning_rows": len(warnings),
        "reconciled": len(rows) == len(candidates) + len(rejected) + copies,
        "ready_for_publication": not rejected,
        "rule_version": RULE_VERSION,
    }
    return ValidationResult(candidates, rejected, warnings, summary, versions)
