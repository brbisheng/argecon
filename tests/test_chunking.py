from __future__ import annotations

from src.common.enums import FileType, ParseStatus, TextQualityFlag
from src.common.schemas import SourceDocument
from src.chunking.chunk_pipeline import ChunkingConfig, chunk_document, inspect_sections


def _build_document(paragraphs: list[str]) -> SourceDocument:
    return SourceDocument(
        doc_id="doc-1",
        region="fj",
        source_path="/tmp/sample.txt",
        file_name="sample.txt",
        file_type=FileType.TXT,
        title="样例政策",
        raw_text="\n\n".join(paragraphs),
        paragraphs=paragraphs,
        parse_status=ParseStatus.SUCCESS,
        source_format_confidence=1.0,
        text_quality_flag=TextQualityFlag.CLEAN,
    )


def test_section_splitter_detects_common_policy_headings() -> None:
    document = _build_document(
        [
            "政策总则",
            "这是导语段。",
            "一、支持对象",
            "面向家庭农场。",
            "第一条 申请条件",
            "年龄符合要求。",
            "1. 申请材料",
            "提供身份证明。",
            "办理流程",
            "按规定提交申请。",
        ]
    )

    sections = inspect_sections(document).sections

    assert [section.title for section in sections] == ["政策总则", "一、支持对象", "第一条 申请条件", "1. 申请材料", "办理流程"]
    assert sections[1].start_paragraph == 2
    assert sections[-1].heading_paragraph == 8


def test_chunk_document_merges_short_paragraphs_and_preserves_traceability() -> None:
    document = _build_document(
        [
            "一、申请对象",
            "面向家庭农场。",
            "需正常经营。",
            "第二条 申请材料",
            "身份证明。",
            "营业执照。",
        ]
    )

    chunks = chunk_document(
        document,
        ChunkingConfig(min_chunk_chars=10, target_chunk_chars=18, max_chunk_chars=60),
    )

    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[0].paragraph_range == (1, 2)
    assert chunks[0].section_title == "一、申请对象"
    assert chunks[0].doc_id == document.doc_id
    assert "面向家庭农场。" in chunks[0].chunk_text
    assert chunks[1].paragraph_range == (4, 5)
    assert chunks[1].section_title == "第二条 申请材料"


def test_chunk_document_splits_long_paragraph_by_sentence_group() -> None:
    long_paragraph = "".join([f"第{i}句说明政策细则。" for i in range(1, 9)])
    document = _build_document(["一、政策内容", long_paragraph])

    chunks = chunk_document(
        document,
        ChunkingConfig(min_chunk_chars=20, target_chunk_chars=40, max_chunk_chars=45),
    )

    assert len(chunks) >= 2
    assert all(chunk.paragraph_range == (1, 1) for chunk in chunks)
    assert all(chunk.section_title == "一、政策内容" for chunk in chunks)
    assert chunks[0].chunk_index == 0
    assert chunks[-1].doc_id == document.doc_id
