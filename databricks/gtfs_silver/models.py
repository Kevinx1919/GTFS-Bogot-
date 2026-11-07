"""Contratos de ejecución compartidos; no realizan consultas ni escrituras."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any

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
        if not self.source_path or not self.source_path.endswith(f"/{self.entity}.txt"):
            raise ValueError(f"source_path debe identificar el archivo {self.entity}.txt seleccionado.")


@dataclass
class PreparedSnapshot:
    """Resultados Spark y métricas pequeñas; los registros permanecen distribuidos."""
    frames: dict[str, Any]
    summary: dict[str, Any]
    reference_versions: dict[str, str]
