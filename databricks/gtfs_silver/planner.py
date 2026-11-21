"""Decisiones del planificador Silver; no consulta Spark ni escribe datos."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
import json
import re
from typing import Any

from gtfs_bronze.contracts import ENTITY_NAMES, RULE_VERSION as BRONZE_RULE_VERSION
from .models import DerivedSnapshotSpec, SOURCE_ENTITY_NAMES

ENTITY_ORDER = ("agency", "routes", "stops", "calendar", "calendar_dates", "service_dates",
                "shape_points", "trips", "frequencies", "stop_times")
SUPPORTED_RULES = {entity: entity + "_v1" for entity in ENTITY_ORDER}


def timestamp(value: Any) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime):
        raise ValueError("La auditoría requiere timestamps válidos.")
    # Spark recupera timestamps como datetime naive bajo una sesión UTC.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def identity(row: dict) -> tuple[str, str]:
    version, sha = row["source_feed_version"], row["source_sha256"]
    date.fromisoformat(version)
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError("Hash inválido en la metadata del planificador.")
    return version, sha


def registry_order(registry: dict) -> list[str]:
    enabled = [name for name, cfg in registry.items() if cfg.get("enabled") is True]
    if any(name not in SUPPORTED_RULES or registry[name].get("validator") != SUPPORTED_RULES[name] for name in enabled):
        raise ValueError("El registro habilita una entidad o regla sin procesador compatible.")
    ordered = []
    while len(ordered) < len(enabled):
        available = [name for name in enabled if name not in ordered and all(
            dep in ordered for dep in registry[name].get("depends_on", []) + registry[name].get("depends_on_if_published", [])
        )]
        if not available:
            raise ValueError("Hay dependencias deshabilitadas, desconocidas o un ciclo en el registro.")
        # Mantengo el orden declarado cuando varias entidades están disponibles.
        ordered.append(available[0])
    return ordered


def bronze_snapshots(events: list[dict]) -> list[dict]:
    """El último STARTED manda; nunca rescato un CLOSED anterior satisfactorio."""
    starts, closes = defaultdict(list), defaultdict(list)
    for row in events:
        if row.get("event_type") == "STARTED": starts[identity(row)].append(row)
        elif row.get("event_type") == "CLOSED": closes[row["quality_run_id"]].append(row)
    result = []
    for key in sorted(starts):
        latest_time = max(timestamp(r["started_at_utc"]) for r in starts[key])
        latest = [r for r in starts[key] if timestamp(r["started_at_utc"]) == latest_time]
        start = latest[0]
        entry = {"key": key, "start": start, "closure": None, "inventory": {}, "reason": ""}
        matches = closes.get(start["quality_run_id"], [])
        if len(latest) != 1 or len(matches) > 1:
            entry["reason"] = "AMBIGUOUS_BRONZE_ATTEMPT"
        elif not matches:
            entry["reason"] = "INCOMPLETE_BRONZE_ATTEMPT"
        else:
            close = matches[0]; entry["closure"] = close
            coherent = (identity(close) == key and timestamp(close["started_at_utc"]) == latest_time
                        and start.get("rule_version") == close.get("rule_version") == BRONZE_RULE_VERSION)
            if not coherent:
                entry["reason"] = "BRONZE_IDENTITY_OR_RULE_MISMATCH"
            elif (close.get("validation_completed") is not True or close.get("ready_for_silver") is not True
                  or close.get("status") not in {"PASSED", "WARNING"} or close.get("blocking_failures") != 0
                  or close.get("warning_policy") != "silver_contracts_v1"
                  or not close.get("total_checks") or not close.get("completed_at_utc")):
                entry["reason"] = "BRONZE_NOT_READY"
            elif timestamp(close["completed_at_utc"]) < latest_time:
                entry["reason"] = "BRONZE_INVALID_COMPLETION_TIME"
            else:
                try:
                    inventory = json.loads(close["entity_inventory_json"])
                    if set(inventory) != ENTITY_NAMES or not re.fullmatch(r"[0-9a-f]{64}", close["result_sha256"]):
                        raise ValueError("Inventario o huella inválidos")
                    for item in inventory.values():
                        if type(item["source_present"]) is not bool:
                            raise ValueError("Presencia inválida")
                        if item["source_present"] and (item["source_row_count"] <= 0 or
                            item["source_row_count"] != item["snapshot_count"] or not item["table_exists"] or
                            type(item["delta_version"]) is not int):
                            raise ValueError("Carga no reconciliada")
                    required = {"agency", "routes", "stops", "trips", "shapes", "stop_times"}
                    if any(not inventory[name]["source_present"] for name in required) or not any(
                        inventory[name]["source_present"] for name in ("calendar", "calendar_dates")
                    ): raise ValueError("Archivos obligatorios ausentes")
                    entry["inventory"] = inventory
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    entry["reason"] = "INVALID_BRONZE_INVENTORY"
        result.append(entry)
    # Los lectores actuales no admiten un hash compartido entre versiones.
    versions = defaultdict(set)
    for entry in result:
        if not entry["reason"]: versions[entry["key"][1]].add(entry["key"][0])
    for entry in result:
        if len(versions[entry["key"][1]]) > 1: entry["reason"] = "HASH_HAS_MULTIPLE_VERSIONS"
    return result


def latest_audits(rows: list[dict]) -> dict[tuple[str, str, str], list[dict]]:
    groups = defaultdict(list)
    for row in rows:
        version, sha = identity(row)
        key = (row["entity"], version, sha)
        groups[key].append(row)
    return {key: [r for r in values if timestamp(r["started_at_utc"]) == max(timestamp(v["started_at_utc"]) for v in values)]
            for key, values in groups.items()}


def build_plan(events: list[dict], audits: list[dict], targets: dict, registry: dict,
               service_dates: dict, *, catalog: str, schema: str, max_snapshots: int = 20,
               max_task_value_bytes: int = 45000) -> dict:
    """Genera un lote de snapshots completos, con decisiones visibles para lo restante."""
    if type(max_snapshots) is not int or not 1 <= max_snapshots <= 100:
        raise ValueError("max_snapshots debe estar entre 1 y 100.")
    if not 1000 <= max_task_value_bytes <= 48000:
        raise ValueError("Límite de task values fuera del rango permitido.")
    order = registry_order(registry)
    lower, upper = service_dates["feed_version_from"], service_dates["feed_version_to"]
    if date.fromisoformat(lower) > date.fromisoformat(upper):
        raise ValueError("Rango de feeds service_dates inválido.")
    DerivedSnapshotSpec(lower, "a" * 64, service_dates["window_start"], service_dates["window_end"])
    latest = latest_audits(audits)
    decisions, items = [], {name: [] for name in order}
    scheduled_snapshots = 0
    for snapshot in bronze_snapshots(events):
        version, sha = snapshot["key"]
        if snapshot["reason"]:
            decisions.append({"entity": "*", "feed_version": version, "snapshot_sha256": sha,
                              "status": "BLOCKED", "reason": snapshot["reason"]})
            continue
        inventory = snapshot["inventory"]; close = snapshot["closure"]
        if any(item.get("table_name") != f"{catalog}.{schema}.bronze_gtfs_{name}" for name, item in inventory.items()):
            decisions.append({"entity": "*", "feed_version": version, "snapshot_sha256": sha,
                              "status": "BLOCKED", "reason": "BRONZE_INVENTORY_TARGET_MISMATCH"})
            continue
        local, states, available_audits = [], {}, {}
        for name in order:
            cfg = registry[name]; source = SOURCE_ENTITY_NAMES.get(name, name)
            target_key = (name, version, sha)
            target = targets.get(target_key, {"exists": False, "rows": 0})
            candidates = latest.get(target_key, [])
            row = {"entity": name, "feed_version": version, "snapshot_sha256": sha,
                   "expected_rule_version": cfg["validator"], "status": "PENDING", "reason": "NOT_PUBLISHED"}
            published = name == "service_dates" or inventory[source]["source_present"]
            if not published:
                row.update(status="BLOCKED" if candidates or target.get("rows", 0) else "NOT_APPLICABLE", reason="SOURCE_NOT_PUBLISHED")
            elif name == "service_dates" and not lower <= version <= upper:
                row.update(status="OUT_OF_SCOPE", reason="SERVICE_DATES_FEED_OUTSIDE_CONFIGURED_RANGE")
            elif target.get("error"):
                row.update(status="BLOCKED", reason=target["error"])
            elif len(candidates) > 1:
                row.update(status="BLOCKED", reason="AMBIGUOUS_SILVER_ATTEMPT")
            elif candidates:
                audit = candidates[0]
                if (audit.get("status") != "SUCCEEDED" or audit.get("silver_committed") is not True
                        or not audit.get("finished_at_utc")):
                    row.update(status="BLOCKED", reason="LATEST_SILVER_ATTEMPT_NOT_SUCCESSFUL")
                elif (type(audit.get("candidate_rows")) is not int or audit["candidate_rows"] < 1
                      or type(audit.get("input_rows")) is not int or audit["input_rows"] < audit["candidate_rows"]
                      or audit.get("rejected_rows") != 0
                      or timestamp(audit["finished_at_utc"]) < timestamp(audit["started_at_utc"])):
                    row.update(status="BLOCKED", reason="INVALID_SUCCESSFUL_AUDIT")
                elif audit.get("target_table") != f"{catalog}.{schema}.silver_gtfs_{name}":
                    row.update(status="BLOCKED", reason="AUDIT_TARGET_MISMATCH")
                elif (not target.get("exists") or target.get("rows") != audit.get("candidate_rows")
                      or target.get("run_ids") != [audit["silver_run_id"]]
                      or target.get("rules") != [audit.get("silver_rule_version")]
                      or target.get("invalid_technical_rows", 0)):
                    row.update(status="BLOCKED", reason="DESTINATION_DOES_NOT_MATCH_AUDIT")
                elif name == "service_dates" and target.get("windows") != [[service_dates["window_start"], service_dates["window_end"]]]:
                    row.update(status="BLOCKED", reason="SERVICE_DATES_WINDOW_REQUIRES_EXPLICIT_MIGRATION")
                elif audit.get("silver_rule_version") != cfg["validator"]:
                    row.update(reason="RULE_CHANGED")
                else:
                    row.update(status="COMPLETE", reason="AUDIT_AND_DESTINATION_MATCH")
                    available_audits[name] = audit
            elif target.get("rows", 0):
                row.update(status="BLOCKED", reason="DESTINATION_WITHOUT_AUDIT")
            dependencies = cfg.get("depends_on", []) + [dep for dep in cfg.get("depends_on_if_published", [])
                           if inventory[SOURCE_ENTITY_NAMES.get(dep, dep)]["source_present"]]
            if row["status"] in {"COMPLETE", "PENDING"}:
                if any(states.get(dep) not in {"COMPLETE", "PENDING"} for dep in dependencies):
                    row.update(status="BLOCKED", reason="DEPENDENCY_NOT_AVAILABLE")
                elif any(states[dep] == "PENDING" for dep in dependencies):
                    row.update(status="PENDING", reason="DEPENDENCY_SCHEDULED")
                elif row["status"] == "COMPLETE" and any(
                    timestamp(available_audits[dep]["finished_at_utc"]) > timestamp(available_audits[name]["started_at_utc"])
                    for dep in dependencies
                ):
                    row.update(status="PENDING", reason="DEPENDENCY_REPUBLISHED")
            states[name] = row["status"]; local.append(row)
        pending = [r for r in local if r["status"] == "PENDING"]
        if pending and scheduled_snapshots >= max_snapshots:
            for row in pending: row.update(status="DEFERRED", reason="SNAPSHOT_BATCH_LIMIT")
        elif pending:
            scheduled_snapshots += 1
            for row in pending:
                name = row["entity"]
                item = {key: row[key] for key in ("entity", "feed_version", "snapshot_sha256", "expected_rule_version")}
                source = SOURCE_ENTITY_NAMES.get(name, name)
                item.update(bronze_quality_run_id=close["quality_run_id"], bronze_result_sha256=close["result_sha256"],
                            bronze_delta_version="" if name == "service_dates" else str(inventory[source]["delta_version"]))
                if name == "service_dates": item.update({key: service_dates[key] for key in ("window_start", "window_end")})
                items[name].append(item)
        decisions.extend(local)
    for name, values in items.items():
        if len(json.dumps(values, ensure_ascii=False).encode("utf-8")) > max_task_value_bytes:
            raise ValueError(f"La lista de {name} excede el límite; reduce max_snapshots.")
    counts = {status: sum(r["status"] == status for r in decisions)
              for status in ("PENDING", "COMPLETE", "BLOCKED", "NOT_APPLICABLE", "OUT_OF_SCOPE", "DEFERRED")}
    status = "BLOCKED" if counts["BLOCKED"] else "READY" if counts["PENDING"] else "NO_WORK"
    return {"planner_version": "silver_planner_v1", "status": status,
            "counts": counts, "work_items": items, "decisions": decisions}
