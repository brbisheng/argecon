"""File scanning and ingestion orchestration."""

from .dispatcher import ParserRegistry, build_default_registry, parse_document
from .manifest import write_jsonl, write_manifest
from .pipeline import IngestionRunResult, PipelineArtifacts, chunk_document, run_ingestion_pipeline
from .report import ReportBuilder, write_report
from .scanner import ScanResult, infer_region, scan_directory

__all__ = [
    "IngestionRunResult",
    "ParserRegistry",
    "PipelineArtifacts",
    "ReportBuilder",
    "ScanResult",
    "build_default_registry",
    "chunk_document",
    "infer_region",
    "parse_document",
    "run_ingestion_pipeline",
    "scan_directory",
    "write_jsonl",
    "write_manifest",
    "write_report",
]
