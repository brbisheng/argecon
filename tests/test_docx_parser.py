from __future__ import annotations

from pathlib import Path

from src.common.enums import ParseStatus
from src.ingest.dispatcher import build_default_registry, parse_document
from src.ingest.scanner import scan_directory
from tests.helpers import write_docx


def test_docx_parser_extracts_paragraphs_title_and_status(tmp_path: Path) -> None:
    source = tmp_path / 'fj' / '样例政策.docx'
    write_docx(source)
    record = scan_directory(tmp_path).records[0]

    result = parse_document(record, registry=build_default_registry())

    assert result.success is True
    assert result.document.title == '测试标题'
    assert result.document.paragraphs == ['测试标题', '贷款额度最高50万元。', '期限12个月，执行利率3.2%。']
    assert '贷款额度最高50万元。' in result.document.raw_text
    assert result.document.parse_status is ParseStatus.SUCCESS
