"""Manifest serialization helpers for ingestion outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.common.io_utils import write_jsonl
from src.common.schemas import ManifestRecord


def write_manifest(records: Iterable[ManifestRecord], output_path: str | Path) -> None:
    """Write manifest records to JSONL."""

    write_jsonl(records, output_path)


__all__ = ["write_jsonl", "write_manifest"]
