from __future__ import annotations

from pathlib import Path

from src.ingest.scanner import infer_region, scan_directory
from tests.helpers import write_docx


def test_scan_directory_finds_supported_files_and_skips_unknown_suffixes(tmp_path: Path) -> None:
    root = tmp_path / '北京农户信贷31'
    write_docx(root / '产品.docx')
    (root / 'notes.tmp').write_text('ignore me', encoding='utf-8')

    scan_result = scan_directory(tmp_path)

    assert len(scan_result.records) == 1
    assert scan_result.records[0].file_name == '产品.docx'
    assert scan_result.records[0].region == '北京'
    assert scan_result.skipped_paths and scan_result.skipped_paths[0].endswith('notes.tmp')
    assert infer_region(root / '产品.docx', tmp_path) == '北京'
