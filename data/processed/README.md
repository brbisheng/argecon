# processed data

这里保留 API / retriever / demo 默认读取的稳定处理产物路径。仓库中提交的空文件只是占位，真正可用的知识库需要先运行 ingestion，并由脚本覆盖这些同名文件。

## 占位文件（仓库内预创建）

以下文件可能在仓库初始状态下为空，用于固定路径与便于挂载；**空文件不能当作可用知识库**：

- `manifest.jsonl`
- `documents.jsonl`
- `chunks.jsonl`
- `kb_chunks.jsonl`

## 运行 ingestion 后生成 / 覆盖的产物

执行 `scripts/run_ingestion.py` 后，处理产物会直接写回 `data/processed/` 根目录，并覆盖同名占位文件：

- `manifest.jsonl`: 原始文件扫描清单。
- `documents.jsonl`: 统一 document 层输出。
- `chunks.jsonl`: document 切块产物。
- `kb_chunks.jsonl`: 供检索层默认优先读取的知识库 chunk。
- `ingestion_report.json`: 导入汇总与失败报告。
- `retrieval_index.json`: 可选的离线检索索引构建产物。
