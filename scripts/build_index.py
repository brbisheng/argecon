"""CLI entrypoint for building a persisted retrieval index from chunk artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.retrieve.index_store import ChunkIndexStore, save_chunk_index


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从 chunks 构建可复用的检索索引。")
    parser.add_argument("--data-dir", default="data/processed", help="chunk 目录，默认读取 data/processed")
    parser.add_argument("--chunk-path", default=None, help="显式指定 chunk 文件路径")
    parser.add_argument(
        "--output",
        default="data/processed/retrieval_index.json",
        help="索引输出 JSON 文件路径",
    )
    return parser


def run_cli(args: argparse.Namespace) -> Path:
    store = ChunkIndexStore(data_dir=args.data_dir)
    index = store.build_index(chunk_path=args.chunk_path)
    output_path = save_chunk_index(index, args.output)
    summary = {
        "output_path": str(output_path),
        "chunk_count": index.metadata.get("chunk_count", 0),
        "source_path": index.metadata.get("source_path"),
        "average_document_length": round(index.average_document_length, 4),
        "vocabulary_size": len(index.document_frequencies),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return output_path


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    run_cli(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
