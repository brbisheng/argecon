"""CLI entrypoint for one-click ingestion from raw files to structured artifacts."""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingest.pipeline import run_ingestion_pipeline


@dataclass(slots=True)
class OutputLayout:
    """Directory layout for staged ingestion artifacts and promoted stable outputs."""

    root: Path
    manifest_path: Path
    documents_dir: Path
    documents_path: Path
    chunks_dir: Path
    chunks_path: Path
    kb_chunks_path: Path
    report_dir: Path
    report_path: Path


def prepare_output_layout(output_root: str | Path) -> OutputLayout:
    """Create the staged subdirectories used by ingestion and the promoted root files."""

    root = Path(output_root)
    layout = OutputLayout(
        root=root,
        manifest_path=root / "manifest.jsonl",
        documents_dir=root / "documents",
        documents_path=root / "documents" / "documents.jsonl",
        chunks_dir=root / "chunks",
        chunks_path=root / "chunks" / "chunks.jsonl",
        kb_chunks_path=root / "chunks" / "kb_chunks.jsonl",
        report_dir=root / "report",
        report_path=root / "report" / "ingestion_report.json",
    )
    for directory in (layout.root, layout.documents_dir, layout.chunks_dir, layout.report_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return layout


def promote_pipeline_outputs(layout: OutputLayout) -> dict[str, Path]:
    """Copy staged artifacts to stable root-level paths for default API/demo consumers."""

    promoted = {
        "manifest": layout.manifest_path,
        "documents": layout.root / "documents.jsonl",
        "chunks": layout.root / "chunks.jsonl",
        "kb_chunks": layout.root / "kb_chunks.jsonl",
        "report": layout.root / "ingestion_report.json",
    }
    staged = {
        "manifest": layout.manifest_path,
        "documents": layout.documents_path,
        "chunks": layout.chunks_path,
        "kb_chunks": layout.kb_chunks_path,
        "report": layout.report_path,
    }
    for key, source in staged.items():
        destination = promoted[key]
        if source == destination:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return promoted


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从原始目录一键生成 data/processed 下的分目录产物，并同步稳定根目录文件。")
    parser.add_argument("input_dir", help="原始文件目录")
    parser.add_argument(
        "--output-root",
        default="data/processed",
        help="输出根目录，脚本会写入 documents/chunks/report 子目录，并同步覆盖根目录稳定产物文件。",
    )
    parser.add_argument("--chunk-size", type=int, default=800, help="chunk 最大字符数")
    parser.add_argument("--chunk-overlap", type=int, default=100, help="chunk 重叠字符数")
    parser.add_argument("--non-recursive", action="store_true", help="只扫描输入目录第一层")
    return parser


def run_cli(args: argparse.Namespace) -> dict[str, Path]:
    layout = prepare_output_layout(args.output_root)
    result = run_ingestion_pipeline(
        input_dir=args.input_dir,
        output_dir=layout.root,
        recursive=not args.non_recursive,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    outputs = promote_pipeline_outputs(layout)
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
