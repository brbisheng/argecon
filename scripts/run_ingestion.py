"""CLI entrypoint for one-click ingestion from raw files to structured artifacts."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingest.pipeline import IngestionRunResult, run_ingestion_pipeline


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从原始目录一键生成 documents/chunks/report 产物。")
    parser.add_argument("input_dir", help="原始文件目录")
    parser.add_argument(
        "--output-root",
        default="data/processed",
        help="输出根目录，脚本会在其下生成 documents/chunks/report 子目录。",
    )
    parser.add_argument("--chunk-size", type=int, default=800, help="chunk 最大字符数")
    parser.add_argument("--chunk-overlap", type=int, default=100, help="chunk 重叠字符数")
    parser.add_argument("--non-recursive", action="store_true", help="只扫描输入目录第一层")
    return parser


def prepare_output_layout(output_root: str | Path) -> dict[str, Path]:
    root = Path(output_root)
    layout = {
        "documents": root / "documents",
        "chunks": root / "chunks",
        "report": root / "report",
        "staging": root / ".pipeline_tmp",
    }
    for path in layout.values():
        path.mkdir(parents=True, exist_ok=True)
    return layout


def promote_pipeline_outputs(result: IngestionRunResult, output_root: str | Path) -> dict[str, Path]:
    layout = prepare_output_layout(output_root)
    destination_map = {
        result.artifacts.manifest_path: layout["documents"] / "manifest.jsonl",
        result.artifacts.documents_path: layout["documents"] / "documents.jsonl",
        result.artifacts.chunks_path: layout["chunks"] / "chunks.jsonl",
        result.artifacts.kb_chunks_path: layout["chunks"] / "kb_chunks.jsonl",
        result.artifacts.report_path: layout["report"] / "ingestion_report.json",
    }
    for source, destination in destination_map.items():
        shutil.copy2(source, destination)
    shutil.rmtree(layout["staging"], ignore_errors=True)
    return destination_map


def run_cli(args: argparse.Namespace) -> dict[str, Path]:
    layout = prepare_output_layout(args.output_root)
    result = run_ingestion_pipeline(
        input_dir=args.input_dir,
        output_dir=layout["staging"],
        recursive=not args.non_recursive,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    outputs = promote_pipeline_outputs(result, args.output_root)
    print(f"[run_ingestion] run_id={result.run_id} files={len(result.manifest_records)} chunks={len(result.chunks)}")
    for source, destination in outputs.items():
        print(f"[run_ingestion] wrote {destination} (from {source.name})")
    return outputs


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    run_cli(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
