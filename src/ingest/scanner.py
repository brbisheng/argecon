"""Directory scanning and source file discovery for ingestion."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from src.common.enums import FileType
from src.common.schemas import ManifestRecord

SUPPORTED_SUFFIXES: dict[str, FileType] = {
    ".doc": FileType.DOC,
    ".docx": FileType.DOCX,
    ".pdf": FileType.PDF,
    ".txt": FileType.TXT,
    ".html": FileType.HTML,
    ".htm": FileType.HTML,
    ".md": FileType.MD,
    ".xls": FileType.XLS,
    ".xlsx": FileType.XLSX,
    ".png": FileType.IMAGE,
    ".jpg": FileType.IMAGE,
    ".jpeg": FileType.IMAGE,
    ".tif": FileType.IMAGE,
    ".tiff": FileType.IMAGE,
}

REGION_ALIASES: dict[str, str] = {
    "adbc": "adbc",
    "fj": "fj",
    "北京农户信贷31": "北京",
    "北京": "北京",
    "beijing": "北京",
    "fujian": "fj",
}


@dataclass(slots=True)
class ScanResult:
    """Discovered files plus scan-level diagnostics."""

    records: list[ManifestRecord]
    skipped_paths: list[str]


def scan_directory(root_dir: str | Path, recursive: bool = True) -> ScanResult:
    """Scan a directory and return manifest-ready records."""

    root_path = Path(root_dir).expanduser().resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Scan root does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Scan root is not a directory: {root_path}")

    iterator: Iterable[Path] = root_path.rglob("*") if recursive else root_path.glob("*")
    records: list[ManifestRecord] = []
    skipped_paths: list[str] = []

    for path in sorted(iterator):
        if not path.is_file():
            continue
        file_type = detect_file_type(path)
        if file_type is FileType.UNKNOWN:
            skipped_paths.append(str(path))
            continue
        records.append(build_manifest_record(path=path, scan_root=root_path, file_type=file_type))

    return ScanResult(records=records, skipped_paths=skipped_paths)


def detect_file_type(path: str | Path) -> FileType:
    """Infer file type from suffix with a stable fallback."""

    suffix = Path(path).suffix.lower()
    return SUPPORTED_SUFFIXES.get(suffix, FileType.UNKNOWN)


def infer_region(path: str | Path, scan_root: str | Path | None = None) -> str:
    """Infer region from the directory structure, optimized for current test_data layout."""

    source_path = Path(path)
    root_path = Path(scan_root).resolve() if scan_root else None

    candidates: list[str] = []
    if root_path:
        try:
            relative_parts = source_path.resolve().relative_to(root_path).parts
            candidates.extend(relative_parts)
        except ValueError:
            pass
    candidates.extend(source_path.parts)

    for part in candidates:
        normalized = part.strip()
        if not normalized:
            continue
        if normalized in REGION_ALIASES:
            return REGION_ALIASES[normalized]
        lowered = normalized.lower()
        if lowered in REGION_ALIASES:
            return REGION_ALIASES[lowered]
        if "北京" in normalized:
            return "北京"
        if normalized.startswith("福建"):
            return "fj"

    return "unknown"


def build_manifest_record(path: Path, scan_root: Path, file_type: FileType | None = None) -> ManifestRecord:
    """Create a manifest record from a discovered file."""

    resolved_path = path.resolve()
    stat = resolved_path.stat()
    discovered_time = datetime.now(timezone.utc)
    checksum = calculate_checksum(resolved_path)
    region = infer_region(resolved_path, scan_root=scan_root)
    doc_id = build_doc_id(region=region, relative_path=resolved_path.relative_to(scan_root))

    return ManifestRecord(
        doc_id=doc_id,
        region=region,
        source_path=str(resolved_path),
        file_name=resolved_path.name,
        file_type=file_type or detect_file_type(resolved_path),
        file_size_bytes=stat.st_size,
        checksum=checksum,
        discovered_time=discovered_time,
    )


def build_doc_id(region: str, relative_path: Path) -> str:
    """Generate a stable document id from region and relative path."""

    digest = hashlib.sha1(str(relative_path).encode("utf-8")).hexdigest()[:10]
    stem = relative_path.stem.replace(" ", "_")
    return f"{region}:{stem}:{digest}"


def calculate_checksum(path: Path) -> str:
    """Hash file content for manifest traceability."""

    hasher = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


__all__ = [
    "REGION_ALIASES",
    "SUPPORTED_SUFFIXES",
    "ScanResult",
    "build_manifest_record",
    "calculate_checksum",
    "detect_file_type",
    "infer_region",
    "scan_directory",
]
