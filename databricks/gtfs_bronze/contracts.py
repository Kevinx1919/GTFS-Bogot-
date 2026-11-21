"""Contrato puro del cierre Bronze, sin dependencias de Spark."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

RULE_VERSION = "bronze_snapshot_v2"
CHECK_FIELDS = (
    "quality_run_id", "checked_at_utc", "source_feed_version", "source_sha256",
    "check_name", "check_category", "entity_name", "severity", "status",
    "observed_value", "expected_value", "details",
)
ENTITY_NAMES = frozenset({
    "agency", "routes", "stops", "trips", "calendar", "calendar_dates", "shapes",
    "stop_times", "frequencies", "fare_attributes", "fare_rules", "feed_info",
})


def quoted_table(value: str) -> str:
    """Recibe una tabla de tres partes, sin comillas previas."""
    parts = value.split(".")
    if len(parts) != 3 or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", p) for p in parts):
        raise ValueError("Usa catálogo.schema.tabla con identificadores simples, sin comillas.")
    return ".".join(f"`{p}`" for p in parts)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_checks(rows: list[tuple]) -> list[tuple]:
    """Rechaza controles contradictorios; consolida copias idénticas de la misma evaluación."""
    by_key = {}
    for original in rows:
        row = tuple(original)
        if len(row) != len(CHECK_FIELDS):
            raise ValueError("El check no cumple el esquema de auditoría Bronze.")
        key = (row[4], row[6], row[7])
        if key in by_key and by_key[key] != row:
            raise ValueError(f"Check contradictorio {key}; reinicia desde el bloque 1.")
        if row[7] not in {"INFO", "WARNING", "BLOCKING"} or row[8] not in {"PASS", "FAIL", "WARN", "NOT_APPLICABLE"}:
            raise ValueError(f"Estado o severidad desconocidos en {key}.")
        if row[8] == "WARN" and row[7] != "WARNING":
            raise ValueError("Una advertencia debe tener severity=WARNING.")
        if row[8] == "FAIL" and row[7] != "BLOCKING":
            raise ValueError("Un fallo Bronze debe tener severity=BLOCKING.")
        by_key[key] = row
    return [by_key[key] for key in sorted(by_key)]


def load_decision(source_count: int, loaded_count: int, wrong_version_count: int) -> bool:
    """Devuelve ya cargado o bloquea evidencia incompleta; nunca borra filas Bronze."""
    if source_count <= 0:
        raise RuntimeError("El archivo publicado no contiene filas. Revisa el contrato antes de cargar.")
    if wrong_version_count:
        raise RuntimeError("El hash tiene otra versión o versión nula. Revisa la identidad; no se añadieron filas.")
    if loaded_count and loaded_count != source_count:
        raise RuntimeError(
            f"Carga Bronze inconsistente: fuente={source_count}, Bronze={loaded_count}. "
            "No se añadieron filas. Revisa la recuperación del snapshot sin borrar el histórico."
        )
    return loaded_count == source_count


def expected_check_keys(entities: dict, identifiers: dict) -> set[tuple[str, str, str]]:
    keys = {("calendar_definition_present", "calendar_definition", "BLOCKING")}
    for name, result in entities.items():
        present, count = result["source_present"], result["snapshot_count"]
        required = name in {"agency", "routes", "stops", "trips", "shapes", "stop_times"}
        keys.add(("source_file_present", name, "BLOCKING" if present or required else "INFO"))
        keys.add(("bronze_snapshot_rows", name, "BLOCKING" if present or count else "INFO"))
        if present:
            keys.add(("source_row_count_matches", name, "BLOCKING"))
            keys.add(("source_schema_evolution", name, result["schema_check_severity"]))
        if present and count:
            keys.add(("bronze_provenance_version", name, "BLOCKING"))
        if name in identifiers:
            if not present or not count:
                keys.add(("critical_identifier_nulls", name, "BLOCKING"))
            elif set(identifiers[name]) - set(result["bronze_columns"]):
                keys.add(("critical_identifier_columns", name, "BLOCKING"))
            else:
                keys.update((f"critical_identifier_{col}", name, "BLOCKING") for col in identifiers[name])
    keys.update((check, entity, "WARNING") for check, entity in [
        ("trips_route_id_exists", "trips"), ("stop_times_trip_id_exists", "stop_times"),
        ("stop_times_stop_id_exists", "stop_times"), ("trips_service_id_exists", "trips"),
    ])
    return keys


def build_closure(
    rows: list[tuple], entities: dict, identifiers: dict, completed_blocks: set[str],
    *, run_id: str, feed_version: str, sha256: str, started_at: datetime,
    coordinator_run_id: str = "",
) -> tuple[list[tuple], dict]:
    """Solo produce un cierre para una evaluación completa y una identidad coherente."""
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ValueError("SHA-256 inválido.")
    datetime.strptime(feed_version, "%Y-%m-%d")
    if not run_id or started_at.tzinfo is None or started_at.utcoffset().total_seconds() != 0:
        raise ValueError("La corrida requiere identificador y fecha UTC.")
    if completed_blocks != {"presence", "identifiers", "schema"} or set(entities) != ENTITY_NAMES:
        raise RuntimeError("Validación incompleta. Ejecuta todos los bloques desde el bloque 1.")
    checks = canonical_checks(rows)
    for row in checks:
        if row[:4] != (run_id, started_at, feed_version, sha256):
            raise ValueError("Hay checks de otra corrida o snapshot; reinicia desde el bloque 1.")
    actual = {(r[4], r[6], r[7]) for r in checks}
    expected = expected_check_keys(entities, identifiers)
    if actual != expected:
        raise RuntimeError(f"Checks incompletos o inesperados: faltan={sorted(expected-actual)}, extras={sorted(actual-expected)}")
    for name, result in entities.items():
        if result["table_exists"] and result.get("delta_version") is None:
            raise RuntimeError(f"Falta versión Delta fijada para {name}.")
    failures = sum(r[7:9] == ("BLOCKING", "FAIL") for r in checks)
    warnings = sum(r[8] == "WARN" for r in checks)
    status = "FAILED" if failures else "WARNING" if warnings else "PASSED"
    inventory = canonical_json(entities)
    # No incluyo UUID o tiempos en la huella del resultado lógico.
    evidence = canonical_json({"checks": [list(r[4:]) for r in checks], "entities": entities, "rule_version": RULE_VERSION})
    summary = {
        "quality_run_id": run_id, "event_type": "CLOSED", "source_feed_version": feed_version, "source_sha256": sha256,
        "rule_version": RULE_VERSION, "started_at_utc": started_at,
        "completed_at_utc": datetime.now(timezone.utc), "status": status,
        "total_checks": len(checks), "blocking_failures": failures, "warning_count": warnings,
        "validation_completed": True, "ready_for_silver": failures == 0,
        "warning_policy": "silver_contracts_v1", "entity_inventory_json": inventory,
        "result_sha256": hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
        "coordinator_run_id": coordinator_run_id,
    }
    return checks, summary
