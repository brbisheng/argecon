# scripts

预留批处理、重建索引、数据检查等脚本。脚本应调用 `src/` 模块，不要把全流程硬编码在单个脚本里。

当前入口：

- `run_ingestion.py`: 从原始目录一键产出 `data/processed/documents/`、`data/processed/chunks/`、`data/processed/report/`，并同步根目录兼容 JSON/JSONL 产物。
- `build_index.py`: 从 `chunks/chunks.jsonl` / `chunks/kb_chunks.jsonl`（或根目录兼容文件）构建并落盘检索索引。
- `demo_query.py`: 默认加载标准知识库文件 `data/processed/chunks/kb_chunks.jsonl`，并兼容根目录同步文件；跑完 ingestion 且确认知识库非空后，无需额外参数即可演示检索 + 证据 + 响应链路。

## 真正可运行的最小顺序

先跑 ingestion，再确认标准知识库文件 `data/processed/chunks/kb_chunks.jsonl` 非空，最后再启动 API 或运行 demo。推荐直接按下面顺序执行：

```bash
python scripts/run_ingestion.py data/raw && \
python - <<'PY'
from pathlib import Path

kb_path = Path("data/processed/chunks/kb_chunks.jsonl")
if not kb_path.exists():
    raise SystemExit(f"missing knowledge base file: {kb_path}")
if kb_path.stat().st_size == 0:
    raise SystemExit(f"knowledge base file is empty: {kb_path}")
print(f"kb ready: {kb_path}")
PY
```

确认非空后，再二选一：

### 启动 API

```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

### 运行 demo_query.py

```bash
python scripts/demo_query.py \
  "我想贷款买化肥，额度和期限是什么？"
```

如果 `data/processed/chunks/kb_chunks.jsonl` 文件为空，`demo_query.py` 和 API 都只会返回 `no_result` fallback。
