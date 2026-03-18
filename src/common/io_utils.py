"""Shared JSON and JSONL writing utilities."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from src.common.enums import StrEnum


def write_json(data: Any, output_path: str | Path, *, indent: int = 2) -> None:
    """Write a JSON document with UTF-8 encoding and auto-created parent directories."""

    destination = _prepare_output_path(output_path)
    with destination.open("w", encoding="utf-8") as file_obj:
        json.dump(_to_jsonable(data), file_obj, ensure_ascii=False, indent=indent)
        file_obj.write("\n")


class JsonlWriter:
    """Context-managed JSONL writer that supports incremental record output."""

    def __init__(self, output_path: str | Path, *, append: bool = False) -> None:
        self.path = _prepare_output_path(output_path)
        self.append = append
        self._file_obj = None

    def __enter__(self) -> "JsonlWriter":
        mode = "a" if self.append else "w"
        self._file_obj = self.path.open(mode, encoding="utf-8")
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def write(self, record: Any) -> None:
        if self._file_obj is None:
            raise RuntimeError("JsonlWriter must be opened before writing records")
        self._file_obj.write(json.dumps(_to_jsonable(record), ensure_ascii=False) + "\n")

    def write_many(self, records: Iterable[Any]) -> None:
        for record in records:
            self.write(record)

    def close(self) -> None:
        if self._file_obj is not None:
            self._file_obj.close()
            self._file_obj = None


def write_jsonl(records: Iterable[Any], output_path: str | Path, *, append: bool = False) -> None:
    """Write JSONL records in batch with UTF-8 encoding and auto-created directories."""

    with JsonlWriter(output_path, append=append) as writer:
        writer.write_many(records)


def append_jsonl_record(record: Any, output_path: str | Path) -> None:
    """Append a single record to a JSONL file."""

    with JsonlWriter(output_path, append=True) as writer:
        writer.write(record)


def _prepare_output_path(output_path: str | Path) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


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


__all__ = ["JsonlWriter", "append_jsonl_record", "write_json", "write_jsonl"]
