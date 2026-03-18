"""Top-level ingestion pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.common.enums import ParseStatus
from src.common.schemas import ChunkRecord, ManifestRecord, ParseResult, SourceDocument
from src.chunking.chunk_pipeline import build_default_chunking_config, chunk_document
from src.ingest.dispatcher import ParserRegistry, parse_document
from src.ingest.manifest import write_jsonl, write_manifest
from src.ingest.report import ReportBuilder, write_report
from src.ingest.scanner import ScanResult, scan_directory

DEFAULT_OUTPUT_FILES = {
    "manifest": "manifest.jsonl",
    "documents": "documents.jsonl",
    "chunks": "chunks.jsonl",
    "kb_chunks": "kb_chunks.jsonl",
    "report": "ingestion_report.json",
}


@dataclass(slots=True)
class PipelineArtifacts:
    """Resolved output paths for a pipeline run."""

    manifest_path: Path
    documents_path: Path
    chunks_path: Path
    kb_chunks_path: Path
    report_path: Path


@dataclass(slots=True)
class IngestionRunResult:
    """Return object for callers that need pipeline outputs."""

    run_id: str
    scan_result: ScanResult
    manifest_records: list[ManifestRecord]
    documents: list[SourceDocument]
    chunks: list[ChunkRecord]
    report_path: Path
    artifacts: PipelineArtifacts


def run_ingestion_pipeline(
    input_dir: str | Path,
    output_dir: str | Path = "data/processed",
    recursive: bool = True,
    registry: ParserRegistry | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> IngestionRunResult:
    """Execute the fixed ingestion flow end to end."""

    started_at = datetime.now(timezone.utc)
    run_id = started_at.strftime("ingestion-%Y%m%dT%H%M%SZ")

    scan_result = scan_directory(input_dir, recursive=recursive)
    manifest_records = list(scan_result.records)
    artifacts = _build_artifacts(output_dir)
    write_manifest(manifest_records, artifacts.manifest_path)

    documents: list[SourceDocument] = []
    chunks: list[ChunkRecord] = []
    report_builder = ReportBuilder(run_id=run_id, started_at=started_at, manifest_records=manifest_records)

    for record in manifest_records:
        result = parse_document(record, registry=registry)
        updated_record = _update_manifest_from_result(record, result)
        documents.append(result.document)

        document_chunks = []
        if result.document.parse_status is not ParseStatus.FAILED:
            document_chunks = chunk_document(
                result.document,
                config=build_default_chunking_config(chunk_size=chunk_size, chunk_overlap=chunk_overlap),
            )
            chunks.extend(document_chunks)

        report_builder.record_result(result, chunk_count=len(document_chunks))
        _replace_manifest_record(manifest_records, updated_record)

    write_manifest(manifest_records, artifacts.manifest_path)
    write_jsonl(documents, artifacts.documents_path)
    write_jsonl(chunks, artifacts.chunks_path)
    write_jsonl(chunks, artifacts.kb_chunks_path)
    report = report_builder.finalize(datetime.now(timezone.utc))
    write_report(report, artifacts.report_path)

    return IngestionRunResult(
        run_id=run_id,
        scan_result=scan_result,
        manifest_records=manifest_records,
        documents=documents,
        chunks=chunks,
        report_path=artifacts.report_path,
        artifacts=artifacts,
    )




def _build_artifacts(output_dir: str | Path) -> PipelineArtifacts:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    return PipelineArtifacts(
        manifest_path=root / DEFAULT_OUTPUT_FILES["manifest"],
        documents_path=root / DEFAULT_OUTPUT_FILES["documents"],
        chunks_path=root / DEFAULT_OUTPUT_FILES["chunks"],
        kb_chunks_path=root / DEFAULT_OUTPUT_FILES["kb_chunks"],
        report_path=root / DEFAULT_OUTPUT_FILES["report"],
    )


def _update_manifest_from_result(record: ManifestRecord, result: ParseResult) -> ManifestRecord:
    record.ingestion_time = result.document.ingestion_time
    record.parse_status = result.document.parse_status
    record.parse_error = result.document.parse_error
    record.needs_manual_review = result.document.needs_manual_review
    return record


def _replace_manifest_record(records: list[ManifestRecord], updated_record: ManifestRecord) -> None:
    for index, record in enumerate(records):
        if record.doc_id == updated_record.doc_id:
            records[index] = updated_record
            return


__all__ = ["IngestionRunResult", "PipelineArtifacts", "run_ingestion_pipeline"]
