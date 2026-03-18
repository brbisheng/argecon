"""Ingestion report generation and persistence."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.common.enums import ParseStatus
from src.common.io_utils import write_json
from src.common.schemas import IngestionReport, ManifestRecord, ParseResult


class ReportBuilder:
    """Accumulate per-file outcomes into an ingestion report."""

    def __init__(self, run_id: str, started_at: datetime, manifest_records: list[ManifestRecord]) -> None:
        self.report = IngestionReport(run_id=run_id, started_at=started_at, manifest_records=manifest_records)
        self.report.total_files = len(manifest_records)

    def record_result(self, result: ParseResult, chunk_count: int) -> None:
        document = result.document
        if document.parse_status is ParseStatus.SUCCESS:
            self.report.parsed_successfully += 1
        elif document.parse_status is ParseStatus.PARTIAL:
            self.report.parsed_partially += 1
        else:
            self.report.parse_failed += 1

        self.report.chunks_created += chunk_count
        if document.ocr_needed:
            self.report.ocr_required += 1
        if document.needs_manual_review:
            self.report.manual_review_required += 1
        if document.parse_error:
            self.report.errors.append(f"{document.source_path}: {document.parse_error}")
        for warning in result.warnings:
            if warning and warning not in self.report.errors:
                self.report.errors.append(f"{document.source_path}: {warning}")

    def finalize(self, finished_at: datetime) -> IngestionReport:
        self.report.finished_at = finished_at
        return self.report


def write_report(report: IngestionReport, output_path: str | Path) -> None:
    """Persist the ingestion report as a JSON document."""

    write_json(report, output_path)


__all__ = ["ReportBuilder", "write_report"]
