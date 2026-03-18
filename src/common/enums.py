"""Shared enumerations used across the ingestion, retrieval, and response pipeline."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Backport-friendly string enum base class."""

    def __str__(self) -> str:
        return self.value


class FileType(StrEnum):
    """Supported source file types discovered during ingestion."""

    DOC = "doc"
    DOCX = "docx"
    PDF = "pdf"
    TXT = "txt"
    HTML = "html"
    MD = "md"
    XLS = "xls"
    XLSX = "xlsx"
    IMAGE = "image"
    UNKNOWN = "unknown"


class ParseStatus(StrEnum):
    """Document parsing lifecycle status."""

    PENDING = "pending"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class TextQualityFlag(StrEnum):
    """Coarse-grained text quality signals for downstream handling."""

    CLEAN = "clean"
    LOW_CONFIDENCE = "low_confidence"
    OCR_NOISY = "ocr_noisy"
    TRUNCATED = "truncated"
    DUPLICATED = "duplicated"
    EMPTY = "empty"
    NEEDS_REVIEW = "needs_review"


class DemandScenario(StrEnum):
    """Common financing demand scenarios used in extraction and economics rules."""

    WORKING_CAPITAL = "working_capital"
    EXPANSION = "expansion"
    EQUIPMENT_PURCHASE = "equipment_purchase"
    CROP_INPUT_PURCHASE = "crop_input_purchase"
    SEASONAL_PRODUCTION = "seasonal_production"
    INFRASTRUCTURE = "infrastructure"
    EMERGENCY_RELIEF = "emergency_relief"
    UNKNOWN = "unknown"


class ConstraintLabel(StrEnum):
    """Normalized constraint labels derived from policy and product documents."""

    COLLATERAL = "collateral"
    CREDIT = "credit"
    GUARANTEE = "guarantee"
    EXISTING_DEBT_CONSTRAINT = "existing_debt_constraint"
    REGION = "region"
    INDUSTRY = "industry"
    LOAN_AMOUNT = "loan_amount"
    TERM = "term"
    INTEREST_RATE = "interest_rate"
    PURPOSE_RESTRICTION = "purpose_restriction"
    REPAYMENT = "repayment"
    ELIGIBILITY = "eligibility"
    MATERIALS = "materials"
    OTHER = "other"


__all__ = [
    "ConstraintLabel",
    "DemandScenario",
    "FileType",
    "ParseStatus",
    "StrEnum",
    "TextQualityFlag",
]
