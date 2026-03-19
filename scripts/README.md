# scripts

预留批处理、重建索引、数据检查等脚本。脚本应调用 `src/` 模块，不要把全流程硬编码在单个脚本里。

当前入口：

- `run_ingestion.py`: 从原始目录一键产出 `data/processed/` 根目录下的稳定 JSON/JSONL 产物。
- `build_index.py`: 从 `chunks.jsonl` / `kb_chunks.jsonl` 构建并落盘检索索引。
- `demo_query.py`: 加载本地 chunks 后直接演示检索 + 证据 + 响应链路。
