from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from src.common.enums import FileType, ParseStatus
from src.common.io_utils import JsonlWriter, append_jsonl_record, write_json, write_jsonl
from src.ingest.dispatcher import build_default_registry, parse_document
from src.ingest.pipeline import run_ingestion_pipeline
from src.ingest.scanner import infer_region, scan_directory

DOCX_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>
  <w:body>
    <w:p><w:r><w:t>测试标题</w:t></w:r></w:p>
    <w:p><w:r><w:t>这里是第一段。</w:t></w:r></w:p>
    <w:p><w:r><w:t>这里是第二段。</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
CONTENT_TYPES_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>
  <Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>
  <Default Extension='xml' ContentType='application/xml'/>
  <Override PartName='/word/document.xml' ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'/>
</Types>
"""
RELS_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>
  <Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' Target='word/document.xml'/>
</Relationships>
"""
DOCX_IMAGE_ONLY_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<w:document
  xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main'
  xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>
  <w:body>
    <w:p>
      <w:r>
        <w:drawing>
          <a:graphic />
        </w:drawing>
      </w:r>
    </w:p>
  </w:body>
</w:document>
"""
DOCX_TITLE_FALLBACK_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>
  <w:body>
    <w:p><w:r><w:t>这里是一个较长的引导性段落，包含完整句号，因此不应被直接当成文档标题。</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val='Heading1'/></w:pPr><w:r><w:t>贷款申请条件</w:t></w:r></w:p>
    <w:p><w:r><w:t>申请人需提供身份证明。</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
DOC_RELS_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'/>
"""


def _write_docx(path: Path, document_xml: str = DOCX_XML) -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        archive.writestr("_rels/.rels", RELS_XML)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", DOC_RELS_XML)



def test_io_utils_write_json_and_jsonl_support_batch_and_incremental_modes(tmp_path: Path) -> None:
    nested_dir = tmp_path / "nested" / "output"
    json_path = nested_dir / "report.json"
    jsonl_path = nested_dir / "records.jsonl"

    write_json({"message": "你好", "count": 2}, json_path)
    write_jsonl([{"id": 1}, {"id": 2}], jsonl_path)
    append_jsonl_record({"id": 3}, jsonl_path)
    with JsonlWriter(jsonl_path, append=True) as writer:
        writer.write({"id": 4})
        writer.write_many([{"id": 5}, {"id": 6}])

    assert json.loads(json_path.read_text(encoding="utf-8"))["message"] == "你好"
    assert [json.loads(line)["id"] for line in jsonl_path.read_text(encoding="utf-8").splitlines()] == [1, 2, 3, 4, 5, 6]


def test_scan_directory_infers_regions_from_current_layout(tmp_path: Path) -> None:
    fj_dir = tmp_path / "fj"
    bj_dir = tmp_path / "北京农户信贷31" / "北京农户信贷31"
    fj_dir.mkdir(parents=True)
    bj_dir.mkdir(parents=True)
    _write_docx(fj_dir / "a.docx")
    _write_docx(bj_dir / "b.docx")

    scan_result = scan_directory(tmp_path)

    assert len(scan_result.records) == 2
    assert {record.region for record in scan_result.records} == {"fj", "北京"}
    assert infer_region(bj_dir / "b.docx", tmp_path) == "北京"


def test_dispatcher_parses_docx_without_pipeline_knowing_parser_details(tmp_path: Path) -> None:
    source = tmp_path / "adbc" / "样例.docx"
    source.parent.mkdir(parents=True)
    _write_docx(source)
    record = scan_directory(tmp_path).records[0]

    result = parse_document(record, registry=build_default_registry())

    assert result.success is True
    assert result.document.file_type is FileType.DOCX
    assert result.document.parse_status is ParseStatus.SUCCESS
    assert result.document.title == "测试标题"
    assert result.document.paragraphs == ["测试标题", "这里是第一段。", "这里是第二段。"]
    assert "这里是第一段。" in result.document.raw_text


def test_docx_title_falls_back_to_high_confidence_heading_when_first_paragraph_is_not_title(tmp_path: Path) -> None:
    source = tmp_path / "adbc" / "产品.docx"
    source.parent.mkdir(parents=True)
    _write_docx(source, DOCX_TITLE_FALLBACK_XML)
    record = scan_directory(tmp_path).records[0]

    result = parse_document(record, registry=build_default_registry())

    assert result.success is True
    assert result.document.title == "贷款申请条件"
    assert result.document.paragraphs == [
        "这里是一个较长的引导性段落，包含完整句号，因此不应被直接当成文档标题。",
        "贷款申请条件",
        "申请人需提供身份证明。",
    ]
    assert result.document.raw_text.splitlines()[1] == "贷款申请条件"


def test_docx_image_only_document_is_flagged_for_manual_review(tmp_path: Path) -> None:
    source = tmp_path / "fj" / "机构介绍.docx"
    source.parent.mkdir(parents=True)
    _write_docx(source, DOCX_IMAGE_ONLY_XML)
    record = scan_directory(tmp_path).records[0]

    result = parse_document(record, registry=build_default_registry())

    assert result.success is False
    assert result.document.title == "机构介绍"
    assert result.document.parse_status is ParseStatus.PARTIAL
    assert result.document.parse_error
    assert result.document.needs_manual_review is True
    assert result.document.ocr_needed is True
    assert result.document.paragraphs == []


def test_docx_invalid_archive_is_marked_failed_instead_of_silent_failure(tmp_path: Path) -> None:
    source = tmp_path / "fj" / "坏文档.docx"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"not-a-zip")
    record = scan_directory(tmp_path).records[0]

    result = parse_document(record, registry=build_default_registry())

    assert result.success is False
    assert result.document.parse_status is ParseStatus.FAILED
    assert result.document.parse_error
    assert result.document.needs_manual_review is True


def test_pipeline_writes_artifacts_and_continues_after_single_file_failure(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "processed"
    good_dir = input_dir / "fj"
    bad_dir = input_dir / "北京农户信贷31"
    good_dir.mkdir(parents=True)
    bad_dir.mkdir(parents=True)

    _write_docx(good_dir / "good.docx")
    (bad_dir / "bad.pdf").write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n")

    result = run_ingestion_pipeline(input_dir=input_dir, output_dir=output_dir)

    manifest_lines = (output_dir / "manifest.jsonl").read_text(encoding="utf-8").strip().splitlines()
    document_lines = (output_dir / "documents.jsonl").read_text(encoding="utf-8").strip().splitlines()
    chunk_lines = (output_dir / "chunks.jsonl").read_text(encoding="utf-8").strip().splitlines()
    kb_chunk_lines = (output_dir / "kb_chunks.jsonl").read_text(encoding="utf-8").strip().splitlines()
    report = json.loads((output_dir / "ingestion_report.json").read_text(encoding="utf-8"))

    documents = [json.loads(line) for line in document_lines]
    chunks = [json.loads(line) for line in chunk_lines]
    kb_chunks = [json.loads(line) for line in kb_chunk_lines]

    document_index = {document["doc_id"]: document for document in documents}

    assert result.report_path == output_dir / "ingestion_report.json"
    assert len(manifest_lines) == 2
    assert len(document_lines) == 2
    assert len(chunk_lines) >= 1
    assert len(kb_chunk_lines) == len(chunk_lines)
    assert report["total_files"] == 2
    assert report["parse_failed"] == 1
    assert report["parsed_successfully"] == 1
    assert report["errors"]
    for document in documents:
        assert document["source_path"]
        assert document["region"]
    for chunk, kb_chunk in zip(chunks, kb_chunks, strict=True):
        assert chunk["doc_id"] in document_index
        assert document_index[chunk["doc_id"]]["source_path"] == chunk["metadata"]["source_path"]
        assert document_index[chunk["doc_id"]]["region"] == chunk["region"]
        assert kb_chunk["chunk_id"] == chunk["chunk_id"]
        assert kb_chunk["source_path"] == chunk["metadata"]["source_path"]


def test_txt_parser_segments_on_blank_lines_and_returns_shared_document_shape(tmp_path: Path) -> None:
    source = tmp_path / "fj" / "notice.txt"
    source.parent.mkdir(parents=True)
    source.write_text("主标题\n\n第一段第一句。\n第一段第二句。\n\n第二段。\n", encoding="utf-8")
    record = scan_directory(tmp_path).records[0]

    result = parse_document(record, registry=build_default_registry())

    assert result.success is True
    assert result.parser_name == "txt_parser"
    assert result.document.title == "主标题"
    assert result.document.paragraphs == ["主标题", "第一段第一句。\n第一段第二句。", "第二段。"]
    assert result.document.raw_text.startswith("主标题")
    assert result.document.parse_status is ParseStatus.SUCCESS


def test_md_parser_splits_headings_and_paragraphs_into_shared_document_shape(tmp_path: Path) -> None:
    source = tmp_path / "fj" / "guide.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "# 申报指南\n\n这里是导语。\n\n## 申请条件\n需要营业执照。\n\n## 材料清单\n身份证明。\n",
        encoding="utf-8",
    )
    record = scan_directory(tmp_path).records[0]

    result = parse_document(record, registry=build_default_registry())

    assert result.success is True
    assert result.parser_name == "md_parser"
    assert result.document.title == "申报指南"
    assert result.document.paragraphs == [
        "# 申报指南",
        "这里是导语。",
        "## 申请条件",
        "需要营业执照。",
        "## 材料清单",
        "身份证明。",
    ]
    assert result.document.parse_status is ParseStatus.SUCCESS


def test_pdf_parser_flags_sparse_extractable_text_for_ocr_review(tmp_path: Path) -> None:
    source = tmp_path / "fj" / "scan_like.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"%PDF-1.4\n1 0 obj\n(Hi)\n(OK)\nendobj\n")
    record = scan_directory(tmp_path).records[0]

    result = parse_document(record, registry=build_default_registry())

    assert result.success is False
    assert result.parser_name == "pdf_parser"
    assert result.document.parse_status is ParseStatus.PARTIAL
    assert result.document.ocr_needed is True
    assert result.document.needs_manual_review is True
    assert result.document.paragraphs == ["Hi", "OK"]


def test_image_parser_stub_returns_skipped_status_without_crashing_pipeline(tmp_path: Path) -> None:
    source = tmp_path / "fj" / "photo.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"\x89PNG\r\n\x1a\n")
    record = scan_directory(tmp_path).records[0]

    result = parse_document(record, registry=build_default_registry())

    assert result.success is False
    assert result.parser_name == "image_parser"
    assert result.document.parse_status is ParseStatus.SKIPPED
    assert result.document.ocr_needed is True
    assert result.document.needs_manual_review is True
    assert result.document.raw_text == ""
