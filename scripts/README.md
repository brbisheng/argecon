# scripts

预留批处理、重建索引、数据检查等脚本。脚本应调用 `src/` 模块，不要把全流程硬编码在单个脚本里。

当前入口：

- `run_ingestion.py`: 从原始目录一键产出 `data/processed/documents/`、`data/processed/chunks/`、`data/processed/report/`，并同步根目录兼容 JSON/JSONL 产物。
- `build_index.py`: 从 `chunks/chunks.jsonl` / `chunks/kb_chunks.jsonl`（或根目录兼容文件）构建并落盘检索索引。
- `demo_query.py`: 默认加载 `data/processed/` 下的 chunk 产物，跑完 ingestion 后无需额外参数即可演示检索 + 证据 + 响应链路。


示例：

```bash
python scripts/run_ingestion.py data/raw
python scripts/demo_query.py "我想贷款买化肥，额度和期限是什么？"
```
