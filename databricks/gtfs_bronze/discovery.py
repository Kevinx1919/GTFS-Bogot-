"""Catálogo y selección Bronze acotados; sin escrituras ni dependencia de Spark."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import hashlib
import re
from typing import Any, Callable
from urllib.parse import urlsplit

from .contracts import canonical_json
from .runtime import download_response

MODES = {"latest_uningested", "explicit_version", "backfill_range"}


def iso_date(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Usa fechas reales con formato AAAA-MM-DD.")
    date.fromisoformat(value)
    return value


def validate_selection(*, selection_mode: str, explicit_version: str = "", start_date: str = "",
                       end_date: str = "", max_versions: int = 1,
                       reprocess_completed: bool = False) -> None:
    if selection_mode not in MODES:
        raise ValueError("selection_mode debe ser latest_uningested, explicit_version o backfill_range.")
    if type(max_versions) is not int or not 1 <= max_versions <= 20:
        raise ValueError("max_versions debe estar entre 1 y 20.")
    if type(reprocess_completed) is not bool:
        raise ValueError("reprocess_completed debe ser booleano.")
    if bool(start_date) != bool(end_date):
        raise ValueError("Configura start_date y end_date juntos.")
    for value in (explicit_version, start_date, end_date):
        if value:
            iso_date(value)
    if start_date and start_date > end_date:
        raise ValueError("start_date no puede ser posterior a end_date.")
    if selection_mode == "explicit_version":
        if not explicit_version or start_date:
            raise ValueError("explicit_version requiere una versión y ningún rango.")
    elif explicit_version:
        raise ValueError("Vacía explicit_version para seleccionar otro modo.")
    if selection_mode == "backfill_range" and not start_date:
        raise ValueError("backfill_range requiere start_date y end_date.")
    if selection_mode == "latest_uningested" and reprocess_completed:
        raise ValueError("El reprocesamiento requiere explicit_version o backfill_range.")


def fetch_catalog(endpoint: str, http_get: Callable[..., Any], *, max_items: int = 5000,
                  max_pages: int = 100, retry_errors: tuple[type[Exception], ...] = (ConnectionError, TimeoutError),
                  sleep: Callable[[float], None] | None = None) -> list[dict]:
    """Falla ante paginación inválida; nunca interpreta una respuesta parcial como catálogo completo."""
    if type(max_items) is not int or not 1 <= max_items <= 10000:
        raise ValueError("max_items debe estar entre 1 y 10000.")
    if type(max_pages) is not int or not 1 <= max_pages <= 100:
        raise ValueError("max_pages debe estar entre 1 y 100.")
    start, items = 1, []
    for _ in range(max_pages):
        def get_page(url: str, **kwargs: Any) -> Any:
            return http_get(url, params={"f": "json", "num": 100, "start": start,
                                        "sortField": "modified", "sortOrder": "desc"}, **kwargs)
        options = {"retry_errors": retry_errors}
        if sleep is not None:
            options["sleep"] = sleep
        response = download_response(endpoint, get_page, **options)
        try:
            payload = response.json()
        finally:
            response.close()
        if not isinstance(payload, dict) or "error" in payload:
            raise RuntimeError("ArcGIS devolvió una respuesta inválida o un error; no actualicé el catálogo.")
        results, next_start = payload.get("results"), payload.get("nextStart")
        if (not isinstance(results, list) or any(not isinstance(item, dict) for item in results)
                or type(next_start) is not int or (next_start != -1 and next_start <= start)):
            raise RuntimeError("Paginación ArcGIS inválida; no actualicé el catálogo.")
        items.extend(results)
        if len(items) > max_items:
            raise ValueError("El catálogo supera max_items; no truncaré la respuesta.")
        if next_start == -1:
            if not items:
                raise RuntimeError("El catálogo respondió sin elementos; no es NO_WORK.")
            return items
        start = next_start
    raise RuntimeError("El catálogo supera max_pages; no persistí una respuesta parcial.")


def normalize_catalog(items: list[dict], *, group_id: str, run_id: str, discovered_at: datetime) -> list[dict]:
    pattern = re.compile(r"GTFS\s+Est[áa]ticos\s+(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
    rows = {}
    for item in items:
        title = item.get("title", "")
        match = pattern.search(title)
        if not match:
            continue
        version = iso_date(match.group(1))
        if not isinstance(item.get("id"), str) or not item["id"]:
            raise ValueError("Un ítem GTFS no tiene identificador del portal.")
        url = item.get("url")
        parsed = urlsplit(url or "")
        direct = bool(parsed.scheme in {"http", "https"} and parsed.netloc and not parsed.username
                      and not parsed.password and parsed.path.lower().endswith(".zip"))
        epoch = lambda key: None if item.get(key) is None else datetime.fromtimestamp(item[key] / 1000, timezone.utc)
        fingerprint = hashlib.sha256("|".join([item["id"], title, url or "", str(item.get("modified", ""))]).encode()).hexdigest()
        row = {"feed_version": version, "portal_item_id": item["id"], "portal_title": title,
               "source_url": url, "is_direct_zip_url": direct, "portal_item_type": item.get("type"),
               "portal_created_at_utc": epoch("created"), "portal_modified_at_utc": epoch("modified"),
               "metadata_fingerprint": fingerprint, "source_group_id": group_id,
               "catalog_run_id": run_id, "discovered_at_utc": discovered_at}
        if item["id"] in rows and rows[item["id"]] != row:
            raise ValueError("El catálogo contiene metadata contradictoria para el mismo ítem.")
        rows[item["id"]] = row
    if not rows:
        raise RuntimeError("No encontré versiones GTFS fechadas; no es NO_WORK.")
    return list(rows.values())


def build_ingestion_plan(catalog_rows: list[dict], events: list[dict], *, observed_versions: set[str] | None = None,
                         selection_mode: str = "latest_uningested", explicit_version: str = "",
                         start_date: str = "", end_date: str = "", max_versions: int = 1,
                         reprocess_completed: bool = False) -> dict:
    # Reutilizo el mismo contrato de cierre que Silver; no duplico sus reglas de elegibilidad.
    from gtfs_silver.planner import bronze_snapshots, timestamp
    validate_selection(selection_mode=selection_mode, explicit_version=explicit_version, start_date=start_date,
                       end_date=end_date, max_versions=max_versions, reprocess_completed=reprocess_completed)
    groups, states = defaultdict(list), defaultdict(list)
    for row in catalog_rows:
        version = iso_date(row["feed_version"])
        if explicit_version and version != explicit_version:
            continue
        if start_date and not start_date <= version <= end_date:
            continue
        groups[version].append(row)
    if explicit_version and explicit_version not in groups:
        raise ValueError("La versión explícita no existe en el catálogo consultado.")
    for state in bronze_snapshots(events):
        states[state["key"][0]].append(state)
    decisions, candidates = [], []
    for version, rows in sorted(groups.items()):
        direct = [row for row in rows if row.get("is_direct_zip_url") is True]
        decision = {"feed_version": version, "status": "BLOCKED", "reason": "NO_DIRECT_ZIP"}
        if direct:
            latest = max(timestamp(row["portal_modified_at_utc"]) for row in direct)
            newest = [row for row in direct if timestamp(row["portal_modified_at_utc"]) == latest]
            if len({row["source_url"] for row in newest}) != 1:
                decision["reason"] = "AMBIGUOUS_SOURCE_URL"
            elif any(state["reason"] for state in states[version]):
                decision["reason"] = next(state["reason"] for state in states[version] if state["reason"])
            elif not states[version] and version in (observed_versions or set()):
                decision["reason"] = "BRONZE_EVIDENCE_WITHOUT_VALID_CLOSURE"
            else:
                reason = "NO_VALIDATED_SNAPSHOT"
                if states[version]:
                    completed = max(timestamp(state["closure"]["completed_at_utc"]) for state in states[version])
                    reason = ("EXPLICIT_REPROCESS" if reprocess_completed else
                              "PORTAL_METADATA_NEWER_THAN_CLOSURE" if latest > completed else "VALIDATED_BRONZE_CLOSURE")
                decision.update(status="COMPLETE" if reason == "VALIDATED_BRONZE_CLOSURE" else "PENDING", reason=reason)
                if decision["status"] == "PENDING":
                    # El hash todavía no existe: Raw resolverá la URL y calculará el contenido real.
                    candidates.append(version)
        decisions.append(decision)
    ordered = sorted(candidates, reverse=selection_mode == "latest_uningested")
    selected = set(ordered[:1 if selection_mode == "latest_uningested" else max_versions])
    for decision in decisions:
        if decision["status"] == "PENDING" and decision["feed_version"] not in selected:
            decision["status"] = "DEFERRED"
    totals = Counter(row["status"] for row in decisions)
    counts = {key: totals[key] for key in ("PENDING", "COMPLETE", "BLOCKED", "DEFERRED")}
    status = "BLOCKED" if counts["BLOCKED"] else "READY" if selected else "NO_WORK"
    work_items = [] if status == "BLOCKED" else [{"feed_version": version} for version in ordered if version in selected]
    if len(canonical_json(work_items).encode("utf-8")) > 45000:
        raise ValueError("El plan supera el límite de task values; reduce max_versions.")
    return {"status": status, "decisions": decisions, "counts": counts, "work_items": work_items}
