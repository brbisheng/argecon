# 给 Codex 的极简启动指令

你现在要快速实现一个 **农村金融信贷 QA 系统 V1**。

## 1. 项目目标
先做一个 **能跑通的最小版本**，不要追求复杂模型。
系统必须完成这几件事：
1. 接收用户问题。
2. 在一个小型知识库中检索最相关段落。
3. 返回相关原文段落与来源。
4. 用 **非幻觉、受控** 的方式生成一段简短描述。
5. 如果段落里有明确条件或数字，抽取出来，形成简单的经济学约束标签。
6. 保留清晰接口，方便后续升级。

---

## 2. 最高优先级硬约束
### A. 不能把系统做成纯 LLM 黑箱
不要用“把全部文档塞给 LLM 然后直接回答”这种方案。
第一版必须显式包含：
- query normalization
- document chunking
- lexical retrieval
- evidence selection
- template-based response building
- simple metadata / regex extraction

LLM 在 V1 中最多只能作为 **可选的局部辅助模块**，不能成为主引擎。

### B. 必须保留“基于知识库查找并引用原文”的能力
回答时必须尽量附带：
- source title
- chunk id
- original paragraph text

### C. 经济学模块不能脱离证据乱推
经济学模块在 V1 中只做：
- 从文本中抽取条件、阈值、利率、期限、担保要求、用途限制
- 给出简单场景标签或约束标签
不要做复杂预测模型，不要脱离原文自由发挥。

### D. 先做最小可运行框架，后续可扩展
代码结构必须模块化，方便以后替换：
- 检索器
- 归一化器
- 证据选择器
- 回答构造器
- 经济学适配器
- 会话记忆

---

## 3. 第一版必须实现的模块
### 3.1 normalizer
输入：用户自然语言问题
输出：归一化后的 query

先用朴素方法：
- lowercase
- punctuation cleanup
- simple tokenizer
- domain synonym mapping
- optional stopword removal

请预留一个 `synonyms.json` 或类似配置文件。

### 3.2 retriever
输入：normalized query
输出：top-k relevant chunks

V1 先用：
- BM25 优先
- TF-IDF 作为备选或对照

不要先上 dense retrieval。

### 3.3 evidence selector
输入：top-k chunks
输出：最相关的 1~2 个句子 + 原文 chunk

V1 先用：
- sentence splitting
- lexical overlap / sentence-level BM25 / simple scoring

### 3.4 response builder
输入：query + selected evidence + metadata + econ tags
输出：结构化回答

回答格式建议固定为：
1. 系统判断的需求场景（如果能判断）
2. 最相关政策依据
3. 简短描述
4. 原文引用
5. 不确定性说明（如果适用）

优先用模板，不要先做自由生成。

### 3.5 econ adapter
输入：selected evidence / metadata
输出：简单 econ labels

V1 先实现这些标签：
- loan_purpose
- horizon
- collateral_required
- guarantee_required
- interest_rate
- subsidy_rate
- eligibility_conditions
- repayment_constraints

先用 regex + rule-based extraction。

### 3.6 session memory
输入：多轮对话历史
输出：当前用户槽位状态

V1 只要支持简单 session state 即可，例如：
- purpose
- amount
- crop_or_activity
- duration
- existing_loan
- guarantee_info

不要先做长期记忆、图记忆、贝叶斯记忆。

---

## 4. 数据与文件结构
请先搭一个清晰、轻量的项目结构：

```text
project_root/
  app/
    main.py
    api.py
    config.py
    pipeline.py
    schemas.py
    utils.py
  modules/
    normalizer.py
    retriever.py
    evidence_selector.py
    response_builder.py
    econ_adapter.py
    session_memory.py
  data/
    raw/
    processed/
    kb_chunks.jsonl
    synonyms.json
    metadata_schema.json
  scripts/
    build_kb.py
    ingest_docs.py
    test_pipeline.py
  tests/
  docs/
    README.md
    FUTURE_WORK.md
  requirements.txt
```

---

## 5. 知识库格式
请把知识库切成 chunk 级别，并存成 `jsonl`。
每条至少包含：

```json
{
  "chunk_id": "doc1_p3_c2",
  "source_title": "某某农村贷款办法",
  "source_type": "policy",
  "text": "……原文段落……",
  "metadata": {
    "loan_type": "short_term_operating",
    "purpose": ["fertilizer", "seed", "feed"],
    "interest_rate": null,
    "subsidy_rate": null,
    "term_limit": null,
    "guarantee_required": null
  }
}
```

如果 metadata 缺失，先允许为空。

---

## 6. 推荐的 API
至少实现一个最简单接口：

### `POST /ask`
输入：
```json
{
  "session_id": "abc123",
  "query": "我想借点钱买化肥，今年还能申请吗？"
}
```

输出：
```json
{
  "normalized_query": "...",
  "retrieved_chunks": [...],
  "selected_evidence": [...],
  "econ_tags": {...},
  "response": {
    "scenario": "short_term_production_turnover",
    "summary": "...",
    "citations": [...],
    "uncertainty": "..."
  },
  "session_state": {...}
}
```

---

## 7. 实施顺序
严格按下面顺序做，不要跳。

### Phase 1
搭项目骨架、依赖、配置、基础 API。

### Phase 2
实现文档 ingest 与 chunk builder。

### Phase 3
实现 BM25/TF-IDF retrieval。

### Phase 4
实现 evidence selection。

### Phase 5
实现 template-based response builder。

### Phase 6
实现 regex/rule econ adapter。

### Phase 7
实现简单 session memory。

### Phase 8
补测试、示例数据、README。

---

## 8. 第一版不要做的事
不要先做这些：
- dense vector retrieval
- graph memory
- GNN
- POMDP dialogue policy
- SRL/NER model training
- BiLSTM-CRF
- RL tuning
- full Bayesian user model
- unrestricted LLM generation

这些全部留到后续版本。

---

## 9. 交付标准
第一版完成时，必须满足：
1. 本地可启动。
2. 能 ingest 一小批政策文档。
3. 能对用户问题返回 top-k 相关 chunks。
4. 能输出带引用的简短回答。
5. 能抽取至少一部分 econ 条件标签。
6. 多轮对话里能保留最基本的 session state。
7. 代码结构清楚，方便后续替换模块。

---

## 10. 未来扩展接口（现在只预留，不实现）
后续可能接入：
- domain ontology
- SRL / frame parser
- better dialogue manager
- active clarification question module
- dense retrieval / hybrid retrieval
- uncertainty calibration
- soft information elicitation
- user type inference
- richer econ scoring / constraints engine

请在设计时尽量通过接口和 class 抽象预留升级空间。

---

## 11. Codex 的工作方式要求
你在输出代码时：
- 先实现最小可运行版本
- 不要过度工程化
- 不要引入不必要的复杂依赖
- 所有模块写清楚 docstring
- 给出一个最小示例数据集
- 给出启动命令
- 给出一个最小测试用例

优先保证：
**能跑、可读、可扩展、证据清楚。**
