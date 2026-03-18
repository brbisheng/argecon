from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

DOCX_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>
  <w:body>
    <w:p><w:r><w:t>测试标题</w:t></w:r></w:p>
    <w:p><w:r><w:t>贷款额度最高50万元。</w:t></w:r></w:p>
    <w:p><w:r><w:t>期限12个月，执行利率3.2%。</w:t></w:r></w:p>
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
DOC_RELS_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'/>
"""


def write_docx(path: Path, document_xml: str = DOCX_XML) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, 'w') as archive:
        archive.writestr('[Content_Types].xml', CONTENT_TYPES_XML)
        archive.writestr('_rels/.rels', RELS_XML)
        archive.writestr('word/document.xml', document_xml)
        archive.writestr('word/_rels/document.xml.rels', DOC_RELS_XML)
