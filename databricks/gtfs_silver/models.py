"""Contratos de ejecución compartidos; no realizan consultas ni escrituras."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any

SOURCE_ENTITY_NAMES = {"shape_points": "shapes"}

TECHNICAL_FIELDS = (
    "source_feed_version", "source_sha256", "source_file_path", "bronze_loaded_at_utc",
)


@dataclass(frozen=True)
class SnapshotSpec:
    feed_version: str
    sha256: str
    source_path: str
    entity: str = "agency"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.entity):
            raise ValueError("Entidad inválida.")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", self.feed_version):
            raise ValueError("feed_version debe usar AAAA-MM-DD.")
        date.fromisoformat(self.feed_version)
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("snapshot_sha256 debe contener 64 caracteres hexadecimales minúsculos.")
        if not self.source_path or not self.source_path.endswith(f"/{self.source_entity}.txt"):
            raise ValueError(f"source_path debe identificar el archivo {self.source_entity}.txt seleccionado.")

    @property
    def source_entity(self) -> str:
        return SOURCE_ENTITY_NAMES.get(self.entity, self.entity)


@dataclass
class PreparedSnapshot:
    """Resultados Spark y métricas pequeñas; los registros permanecen distribuidos."""
    frames: dict[str, Any]
    summary: dict[str, Any]
    reference_versions: dict[str, str]


@dataclass(frozen=True)
class DerivedSnapshotSpec:
    """Identidad de una derivación; no inventa un TXT ni una ruta Raw."""
    feed_version: str
    sha256: str
    window_start: str
    window_end: str
    entity: str = "service_dates"

    def __post_init__(self) -> None:
        if self.entity != "service_dates":
            raise ValueError("La especificación derivada solo admite service_dates.")
        for value in (self.feed_version, self.window_start, self.window_end):
            if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError("Las fechas de la derivación deben usar AAAA-MM-DD.")
            date.fromisoformat(value)
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("snapshot_sha256 debe contener 64 caracteres hexadecimales minúsculos.")
        days = (date.fromisoformat(self.window_end) - date.fromisoformat(self.window_start)).days + 1
        if not 1 <= days <= 366:
            raise ValueError("La ventana de service_dates_v1 debe abarcar entre 1 y 366 días; no se recorta automáticamente.")
