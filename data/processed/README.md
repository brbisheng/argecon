# processed data

这里保留稳定的处理产物路径，支持重复运行与增量更新。

- `manifest.jsonl`: 原始文件扫描清单。
- `documents.jsonl`: 统一 document 层输出。
- `chunks.jsonl`: document 切块产物。
- `kb_chunks.jsonl`: 供检索层使用的知识库 chunk。
- `ingestion_report.json`: 导入汇总与失败报告。
