"""CLI entrypoint for one-click ingestion from raw files to structured artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingest.pipeline import run_ingestion_pipeline


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从原始目录一键生成 data/processed 根目录下的稳定产物。")
    parser.add_argument("input_dir", help="原始文件目录")
    parser.add_argument(
        "--output-root",
        default="data/processed",
        help="输出根目录，脚本会直接覆盖该目录下的稳定产物文件。",
    )
    parser.add_argument("--chunk-size", type=int, default=800, help="chunk 最大字符数")
    parser.add_argument("--chunk-overlap", type=int, default=100, help="chunk 重叠字符数")
    parser.add_argument("--non-recursive", action="store_true", help="只扫描输入目录第一层")
    return parser


def run_cli(args: argparse.Namespace) -> dict[str, Path]:
    result = run_ingestion_pipeline(
        input_dir=args.input_dir,
        output_dir=args.output_root,
        recursive=not args.non_recursive,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    outputs = {
        "manifest": result.artifacts.manifest_path,
        "documents": result.artifacts.documents_path,
        "chunks": result.artifacts.chunks_path,
        "kb_chunks": result.artifacts.kb_chunks_path,
        "report": result.artifacts.report_path,
    }
    print(f"[run_ingestion] run_id={result.run_id} files={len(result.manifest_records)} chunks={len(result.chunks)}")
    for label, destination in outputs.items():
        print(f"[run_ingestion] wrote {label}: {destination}")
    return outputs


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    run_cli(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
