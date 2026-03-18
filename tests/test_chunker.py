from __future__ import annotations

from src.common.enums import FileType, ParseStatus, TextQualityFlag
from src.common.schemas import SourceDocument
from src.chunking.chunk_pipeline import ChunkingConfig, chunk_document


def test_chunker_generates_traceable_chunks_from_document() -> None:
    document = SourceDocument(
        doc_id='doc-1',
        region='北京',
        source_path='/tmp/policy.docx',
        file_name='policy.docx',
        file_type=FileType.DOCX,
        title='设施农业贷款政策',
        raw_text='一、申请对象\n面向家庭农场。\n需正常经营。\n二、申请材料\n营业执照。',
        paragraphs=['一、申请对象', '面向家庭农场。', '需正常经营。', '二、申请材料', '营业执照。'],
        parse_status=ParseStatus.SUCCESS,
        source_format_confidence=1.0,
        text_quality_flag=TextQualityFlag.CLEAN,
    )

    chunks = chunk_document(document, ChunkingConfig(min_chunk_chars=10, target_chunk_chars=16, max_chunk_chars=48))

    assert len(chunks) == 2
    assert chunks[0].doc_id == 'doc-1'
    assert chunks[0].section_title == '一、申请对象'
    assert chunks[0].paragraph_range == (1, 2)
    assert '家庭农场' in chunks[0].chunk_text
