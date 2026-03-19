# argecon

## 工程结构

本仓库先固定一条可扩展的数据与问答链路：

```text
原始文件 -> document -> chunk -> retrieval -> response
```

所有后续代码都应围绕这条链路拆分到独立模块，避免把扫描、解析、切块、检索、证据选择、抽取、经济学规则、响应生成混进一个大脚本。

## 目录职责

- `config/`: 稳定配置入口，包括全局设置、同义词、地区映射、停用词。
- `data/raw/`: 原始输入文件，保留地区目录与源文件形态。
- `data/processed/`: ingestion 产物与中间件落盘路径，保留 `documents/`、`chunks/`、`report/` 子目录，并同步根目录兼容文件。
- `src/common/`: 通用 schema、IO、日志、常量等基础能力。
- `src/ingest/`: 原始文件扫描、加载、导入流程编排。
- `src/parsers/`: 按文件格式分发的解析器，实现 raw file -> document。
- `src/chunking/`: 文档切块，实现 document -> chunk。
- `src/normalize/`: 问题归一化、同义词映射、查询重写。
- `src/retrieve/`: 基于 chunk 的检索与排序。
- `src/evidence/`: 证据句选择、置信度与引用组织。
- `src/extract/`: 从证据中抽取参数、规则字段与结构化信息。
- `src/econ/`: 经济学解释、约束标签与简单规则计算。
- `src/memory/`: 轻量会话状态与槽位更新。
- `src/response/`: 模板与响应组装，实现 retrieval -> response。
- `src/api/`: 对外接口层，仅负责编排，不承载核心业务逻辑。
- `scripts/`: 独立运维与批处理脚本，只调用模块，不内嵌全链路业务。
- `tests/`: 按模块验证链路各环节。

## 处理产物约定

`data/processed/` 采用“分目录 + 根目录兼容文件”的约定：ingestion 的主产物写入子目录，API / demo / retriever 默认也能直接从根目录稳定文件或 `chunks/` 子目录发现数据。

- `manifest.jsonl`
- `documents/documents.jsonl`
- `chunks/chunks.jsonl`
- `chunks/kb_chunks.jsonl`
- `report/ingestion_report.json`
- 兼容同步：`documents.jsonl`、`chunks.jsonl`、`kb_chunks.jsonl`、`ingestion_report.json`

## 推荐开发原则

1. 先扫描原始文件并记录 manifest。
2. 将每个原始文件转换成统一 document 结构。
3. 从 document 切分出 chunk，并保留可追溯 metadata。
4. 所有检索逻辑只面向 chunk 层。
5. 响应生成必须引用 retrieval / evidence 的结果。

## 快速开始

```bash
python scripts/run_ingestion.py data/raw
python scripts/demo_query.py "我想贷款买化肥，额度和期限是什么？"
```

运行完 ingestion 后，不加额外参数即可直接查询；默认检索会优先读取 `data/processed/chunks/kb_chunks.jsonl`，并兼容根目录同步文件。
