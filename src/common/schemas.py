"""Core shared data objects for the document-to-answer pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .enums import ConstraintLabel, DemandScenario, FileType, ParseStatus, TextQualityFlag


@dataclass(slots=True)
class SourceDocument:
    """Normalized file-level representation produced by parsers."""

    doc_id: str
    region: str
    source_path: str
    file_name: str
    file_type: FileType = FileType.UNKNOWN
    title: str = ""
    raw_text: str = ""
    paragraphs: list[str] = field(default_factory=list)
    parse_status: ParseStatus = ParseStatus.PENDING
    parse_error: str | None = None
    source_format_confidence: float = 0.0
    text_quality_flag: TextQualityFlag = TextQualityFlag.CLEAN
    needs_manual_review: bool = False
    ocr_needed: bool = False
    ingestion_time: datetime | None = None


@dataclass(slots=True)
class ChunkRecord:
    """Chunk-level retrieval unit traceable back to a source document."""

    chunk_id: str
    doc_id: str
    region: str
    source_title: str
    chunk_text: str
    chunk_index: int
    section_title: str | None = None
    page_no: int | None = None
    paragraph_range: tuple[int, int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ManifestRecord:
    """Manifest entry describing a discovered source file before or during parsing."""

    doc_id: str
    region: str
    source_path: str
    file_name: str
    file_type: FileType = FileType.UNKNOWN
    file_size_bytes: int | None = None
    checksum: str | None = None
    discovered_time: datetime | None = None
    ingestion_time: datetime | None = None
    parse_status: ParseStatus = ParseStatus.PENDING
    parse_error: str | None = None
    needs_manual_review: bool = False


@dataclass(slots=True)
class ParseResult:
    """Parser output that couples a document with runtime diagnostics."""

    document: SourceDocument
    success: bool
    warnings: list[str] = field(default_factory=list)
    parser_name: str | None = None
    elapsed_ms: int | None = None


@dataclass(slots=True)
class IngestionReport:
    """Aggregate ingestion statistics for a batch run."""

    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    total_files: int = 0
    parsed_successfully: int = 0
    parsed_partially: int = 0
    parse_failed: int = 0
    chunks_created: int = 0
    ocr_required: int = 0
    manual_review_required: int = 0
    errors: list[str] = field(default_factory=list)
    manifest_records: list[ManifestRecord] = field(default_factory=list)


@dataclass(slots=True)
class RetrievedChunk:
    """Retrieved chunk with ranking metadata used by evidence selection."""

    chunk: ChunkRecord
    retrieval_score: float
    retrieval_rank: int | None = None
    match_terms: list[str] = field(default_factory=list)
    retriever_name: str | None = None


@dataclass(slots=True)
class SelectedEvidence:
    """Evidence sentence or span selected from a retrieved chunk."""

    evidence_id: str
    chunk_id: str
    doc_id: str
    evidence_text: str
    rationale: str = ""
    confidence: float = 0.0
    citation_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExtractedParameters:
    """Structured parameters extracted from evidence for economics reasoning."""

    demand_scenario: DemandScenario = DemandScenario.UNKNOWN
    constraint_labels: list[ConstraintLabel] = field(default_factory=list)
    loan_amount: float | None = None
    loan_amount_upper_limit: float | None = None
    loan_term_months: int | None = None
    interest_rate: float | None = None
    subsidy_rate: float | None = None
    effective_rate: float | None = None
    collateral_required: bool | None = None
    collateral_requirement_text: str | None = None
    guarantee_required: bool | None = None
    guarantee_requirement_text: str | None = None
    target_entities: list[str] = field(default_factory=list)
    usage_restrictions: list[str] = field(default_factory=list)
    repayment_constraints: list[str] = field(default_factory=list)
    raw_slots: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EconResult:
    """Economics/rule-engine output used to formulate the final answer."""

    conclusion: str
    confidence: float = 0.0
    demand_scenario: DemandScenario = DemandScenario.UNKNOWN
    constraint_labels: list[ConstraintLabel] = field(default_factory=list)
    estimated_cost: float | None = None
    suggested_actions: list[str] = field(default_factory=list)
    reasoning_steps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SessionState:
    """Lightweight conversational memory shared across turns."""

    session_id: str
    user_id: str | None = None
    current_region: str | None = None
    normalized_query: str | None = None
    demand_scenario: DemandScenario = DemandScenario.UNKNOWN
    extracted_parameters: ExtractedParameters | None = None
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
    selected_evidence: list[SelectedEvidence] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime | None = None


@dataclass(slots=True)
class QueryResponse:
    """Final structured response returned by the API or application layer."""

    answer: str
    session_state: SessionState
    evidence: list[SelectedEvidence] = field(default_factory=list)
    extracted_parameters: ExtractedParameters | None = None
    econ_result: EconResult | None = None
    follow_up_questions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "ChunkRecord",
    "EconResult",
    "ExtractedParameters",
    "IngestionReport",
    "ManifestRecord",
    "ParseResult",
    "QueryResponse",
    "RetrievedChunk",
    "SelectedEvidence",
    "SessionState",
    "SourceDocument",
]
