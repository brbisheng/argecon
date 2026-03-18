"""Manifest serialization helpers for ingestion outputs."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from src.common.enums import StrEnum
from src.common.schemas import ManifestRecord


def write_manifest(records: Iterable[ManifestRecord], output_path: str | Path) -> None:
    """Write manifest records to JSONL."""

    write_jsonl(records, output_path)


def write_jsonl(records: Iterable[Any], output_path: str | Path) -> None:
    """Write an iterable of serializable records to a JSONL file."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as file_obj:
        for record in records:
            file_obj.write(json.dumps(_to_jsonable(record), ensure_ascii=False) + "\n")


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    return value


__all__ = ["write_jsonl", "write_manifest"]
