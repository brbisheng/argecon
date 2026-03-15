# Rural Credit QA System V1
## Codex Execution Brief + Project Guidance

## 1. Project one-sentence definition
Build a **small-knowledge-base, evidence-grounded rural credit QA system** for farmers.
The first version must **run reliably with simple methods**: retrieve relevant policy paragraphs, show the evidence, provide a short controlled description, and optionally compute a small economics-based interpretation from extracted policy parameters.

This is **not** a generic chatbot.
This is a **retrieval-first, evidence-first, rule-assisted, economics-aware QA skeleton** that can later connect smoothly to more advanced computational linguistics and quantitative economics modules.

---

## 2. Non-negotiable constraints
These are hard project constraints and must shape all implementation choices.

### 2.1 Must not rely on LLM API for core system logic
Do **not** build the system as:
- user question -> send everything to LLM -> get answer

Core logic must be implemented with explicit modules such as:
- text normalization
- synonym mapping
- paragraph chunking
- BM25 / TF-IDF retrieval
- sentence scoring
- metadata extraction
- regex / rule-based parameter extraction
- template-based response building
- session memory slot update

LLM, if used at all later, should be optional and peripheral, not the engine.

### 2.2 Knowledge base is small and official data is limited
The system must not hallucinate or pretend to know missing facts.
The system must:
- search the existing knowledge base first
- show evidence explicitly
- state uncertainty when evidence is weak
- avoid unsupported claims

### 2.3 Economics is not decoration
Economics must enter the system as **structure**, not as a paragraph in the report.
In V1, economics should appear as:
- demand-type labels
- constraint labels
- policy parameter extraction
- simple rule-based cost / eligibility interpretation

### 2.4 V1 must run quickly, but architecture must stay extensible
The first version should be simple enough to implement fast.
At the same time, module boundaries must be clear so future upgrades can be attached without rewriting the whole system.

---

## 3. What V1 must do
V1 only needs to complete the following core functions.

### 3.1 Accept a user question in natural language
Examples:
- “我想借点钱买化肥，去年还有一点没还完，现在还能不能申请？”
- “养十头牛的话利息怎么算？”
- “合作社成员能不能申请贴息贷款？”

### 3.2 Normalize the question
Convert messy user wording into a more stable internal query representation.
Examples:
- “借点钱 / 周转 / 垫钱” -> “贷款 / 流动资金”
- “买肥料 / 买种子 / 买饲料” -> “农业生产资料投入”
- “还不上 / 没还完 / 拖着” -> “未结清贷款 / 展期 / 续贷相关风险”

### 3.3 Retrieve relevant knowledge base paragraphs
Use a simple, strong baseline:
- BM25 preferred
- TF-IDF acceptable as baseline or fallback

Return top-k paragraphs with scores and source metadata.

### 3.4 Extract the most relevant sentence(s)
From the retrieved paragraphs, choose the most relevant 1 to 2 sentences using simple methods such as:
- lexical overlap
- sentence-level BM25
- Jaccard similarity
- TextRank later if useful

### 3.5 Build a controlled response
The answer must contain:
1. detected demand scenario
2. supporting policy evidence
3. short controlled description
4. optional simple economics interpretation if parameters are available

### 3.6 Maintain lightweight session memory
Store only a few structured slots for the current conversation, for example:
- loan purpose
- product or crop
- amount
- time horizon
- whether there is existing debt
- whether user mentioned guarantor / cooperative / collateral

This is enough for V1.
Do not build graph memory or complex evolving memory in V1.

---

## 4. What V1 must NOT do
Do not spend time on these in the first version.

- no POMDP dialogue policy
- no GNN memory
- no BiLSTM-CRF training pipeline
- no SRL model training
- no dense vector retrieval as a dependency for launch
- no fully generative answer engine
- no long-form “smart” policy explanation without evidence
- no attempt to infer facts that are absent from the knowledge base

These can become future modules.
They must not block V1.

---

## 5. System concept in one concrete pipeline
Use the following pipeline.

User question
-> normalizer
-> retriever
-> evidence selector
-> parameter extractor
-> economics adapter
-> response builder
-> answer with evidence

A good mental picture is a small wooden desk with labeled trays.
One tray holds normalized query words.
One tray holds retrieved policy paragraphs.
One tray holds extracted numbers like interest rate and subsidy.
The final tray holds the response template.
Each tray is visible and inspectable.
Nothing should behave like a sealed black box.

---

## 6. Recommended repository structure
Use a simple Python project layout.

```text
rural-credit-qa/
├─ README.md
├─ requirements.txt
├─ config/
│  ├─ settings.yaml
│  ├─ synonym_map.yaml
│  └─ stopwords.txt
├─ data/
│  ├─ raw/
│  │  └─ official_docs/
│  ├─ processed/
│  │  ├─ kb_chunks.jsonl
│  │  ├─ metadata.json
│  │  └─ inverted_index.pkl
│  └─ examples/
│     └─ sample_queries.json
├─ src/
│  ├─ ingest/
│  │  ├─ loader.py
│  │  ├─ chunker.py
│  │  └─ metadata_builder.py
│  ├─ normalize/
│  │  ├─ tokenizer.py
│  │  ├─ synonym_normalizer.py
│  │  └─ query_rewriter.py
│  ├─ retrieve/
│  │  ├─ bm25_retriever.py
│  │  ├─ tfidf_retriever.py
│  │  └─ rank_fusion.py
│  ├─ evidence/
│  │  ├─ sentence_selector.py
│  │  └─ confidence.py
│  ├─ extract/
│  │  ├─ regex_extractors.py
│  │  ├─ metadata_rules.py
│  │  └─ parameter_parser.py
│  ├─ econ/
│  │  ├─ demand_classifier.py
│  │  ├─ constraint_rules.py
│  │  └─ simple_calculator.py
│  ├─ memory/
│  │  ├─ session_state.py
│  │  └─ slot_updater.py
│  ├─ response/
│  │  ├─ templates.py
│  │  └─ response_builder.py
│  ├─ api/
│  │  └─ app.py
│  └─ utils/
│     ├─ io.py
│     ├─ logging.py
│     └─ evaluation.py
├─ tests/
│  ├─ test_normalizer.py
│  ├─ test_retriever.py
│  ├─ test_extractors.py
│  ├─ test_econ_rules.py
│  └─ test_response_builder.py
└─ docs/
   ├─ architecture.md
   ├─ roadmap.md
   └─ annotation_guide.md
```

---

## 7. Knowledge base data design
The knowledge base should be chunked at paragraph or rule-item level.
A chunk should be small enough to retrieve precisely, but large enough to preserve policy meaning.

Recommended chunk fields:

```json
{
  "chunk_id": "policy_001_chunk_003",
  "doc_id": "policy_001",
  "title": "某县畜牧业贴息贷款管理办法",
  "section": "第二条 贷款对象",
  "text": "符合条件的养殖户......",
  "source_type": "official_policy",
  "region": "county_x",
  "policy_type": "livestock_subsidized_loan",
  "effective_date": "2025-01-01",
  "tags": ["畜牧", "贴息", "贷款对象"],
  "econ_metadata": {
    "loan_category": "production",
    "possible_parameters": ["interest_rate", "subsidy", "min_scale"],
    "demand_scenario_hint": ["livestock_expansion", "short_term_working_capital"]
  }
}
```

Important rule:
Text content and metadata must stay separate.
Do not mix extracted guesses into the raw text.

---

## 8. V1 module specifications

## 8.1 Ingestion module
### Goal
Turn raw policy files into clean paragraph-level chunks.

### Minimum tasks
- load txt / docx / pdf-converted text
- split by title, section, paragraph, bullet item
- assign stable chunk IDs
- store JSONL chunks

### Output
`data/processed/kb_chunks.jsonl`

---

## 8.2 Normalization module
### Goal
Map farmer-style wording into more stable internal search terms.

### V1 method
- dictionary-based synonym mapping
- light regex rules
- simple token cleanup
- optional jieba for Chinese tokenization

### Example synonym map
```yaml
借点钱: 贷款
周转: 流动资金
垫钱: 流动资金
买肥料: 农业生产资料投入
买种子: 农业生产资料投入
买饲料: 农业生产资料投入
没还完: 未结清贷款
还不上: 逾期风险
续一下: 续贷
展一下: 展期
```

### Output
```json
{
  "original_query": "我想借点钱买化肥，去年还有一点没还完",
  "normalized_query": "贷款 农业生产资料投入 未结清贷款",
  "detected_terms": ["贷款", "农业生产资料投入", "未结清贷款"]
}
```

---

## 8.3 Retrieval module
### Goal
Find the most relevant policy chunks.

### V1 method
- implement BM25 first
- optionally implement TF-IDF as baseline / fallback

### Output
Top-k list like:
```json
[
  {
    "chunk_id": "policy_004_chunk_002",
    "score": 9.27,
    "title": "农业生产经营贷款办法",
    "text": "......"
  }
]
```

### Notes
- keep retrieval inspectable
- save scores for debugging
- no opaque retrieval logic

---

## 8.4 Evidence selection module
### Goal
Within the top retrieved paragraphs, select the 1 to 2 most relevant sentences.

### V1 method
- split paragraph into sentences
- compute lexical overlap with normalized query
- rank sentences
- keep top 1 to 2 sentences

### Output
```json
{
  "selected_sentences": [
    "购买种子、化肥、饲料等生产资料可申请短期经营贷款。",
    "存在未结清贷款的，应按续贷或展期规定另行审核。"
  ]
}
```

---

## 8.5 Parameter extraction module
### Goal
Extract policy parameters that can feed economics logic.

### Candidate parameters
- interest_rate
- subsidy_rate
- min_scale
- max_amount
- max_term
- eligible_subject
- collateral_requirement
- guarantor_requirement

### V1 method
- regex
- rule-based patterns
- metadata lookup

### Example output
```json
{
  "interest_rate": 0.04,
  "subsidy_rate": 0.02,
  "min_scale": 5,
  "max_term_months": 12
}
```

---

## 8.6 Economics adapter module
### Goal
Convert retrieved evidence into a small structured economics interpretation.

### V1 should only do simple things
1. classify demand scenario
2. classify main constraint type
3. compute very simple derived values if policy parameters are clear

### Demand scenarios for V1
- short_term_working_capital
- livestock_expansion
- crop_input_purchase
- disaster_recovery
- renewal_or_extension
- cooperative_based_application

### Constraint types for V1
- existing_debt_constraint
- collateral_constraint
- guarantor_constraint
- eligibility_uncertain
- scale_below_threshold
- interest_subsidy_available

### Example output
```json
{
  "demand_scenario": "crop_input_purchase",
  "constraint_labels": ["existing_debt_constraint"],
  "econ_note": "This looks like a short-term production input financing need with potential renewal review risk.",
  "simple_calc": {
    "effective_rate": 0.02
  }
}
```

Important:
Do not produce fake economics conclusions.
Only compute from explicit evidence.

---

## 8.7 Session memory module
### Goal
Store structured conversation state for the current session.

### V1 slots
- purpose
- crop_or_livestock
- amount
- horizon
- existing_debt
- cooperative
- guarantor
- collateral

### Example state
```json
{
  "purpose": "农业生产资料投入",
  "crop_or_livestock": "养牛",
  "amount": null,
  "horizon": "12个月内",
  "existing_debt": true,
  "cooperative": false,
  "guarantor": null,
  "collateral": null
}
```

### Notes
V1 memory is session slot memory only.
Later it can evolve into a more dynamic state model.

---

## 8.8 Response builder module
### Goal
Assemble the final answer in a controlled format.

### Recommended V1 response format
```text
[系统判断的需求场景]
短期生产周转 / 农业生产资料投入

[最相关政策依据]
《农业生产经营贷款办法》第X条：购买种子、化肥、饲料等生产资料可申请短期经营贷款。
《续贷与展期审核细则》第Y条：存在未结清贷款的，应按续贷或展期规定另行审核。

[简短描述]
根据当前检索到的政策内容，购买化肥属于生产性投入，通常可进入短期经营贷款范围。但你提到去年还有未结清贷款，因此这部分可能不按普通首次申请处理，而要进一步看续贷或展期规则。

[如果能计算则给出简单经济学解释]
如果适用基准利率4%且贴息2%，则表面资金成本可粗略理解为2%。但是否能批，关键仍取决于未结清贷款状态和审核条件。
```

### Important rules
- always show evidence
- do not overstate certainty
- if evidence is weak, say so explicitly
- if no relevant chunk is found, return a controlled fallback message

---

## 9. API design for V1
Keep the interface small and stable.

### Endpoint 1
`POST /query`

Input:
```json
{
  "session_id": "abc123",
  "user_query": "我想借点钱买化肥，去年还有一点没还完，现在还能不能申请？"
}
```

Output:
```json
{
  "normalized_query": "贷款 农业生产资料投入 未结清贷款",
  "retrieved_chunks": [...],
  "selected_sentences": [...],
  "extracted_parameters": {...},
  "econ_result": {...},
  "session_state": {...},
  "final_response": "..."
}
```

### Endpoint 2
`GET /health`

### Endpoint 3
`POST /reload_kb`
Optional for local development.

---

## 10. Immediate implementation order for Codex
Codex should implement in this order.
Do not rearrange unless necessary.

### Phase 1: minimal runnable skeleton
1. create repo structure
2. implement chunk loader
3. implement simple chunk JSONL builder
4. implement synonym map loader
5. implement normalizer
6. implement BM25 retriever
7. implement sentence selector
8. implement response template builder
9. expose `/query` API
10. run a local demo

### Phase 2: economics-aware upgrade
11. add metadata fields
12. add regex parameter extraction
13. add demand scenario classifier with rules
14. add constraint labels with rules
15. add simple effective-rate calculator
16. insert economics block into response

### Phase 3: session support and testing
17. add session slot state
18. update slots from each query
19. write tests for retrieval and extraction
20. add logging and debug traces

### Phase 4: packaging and demo polish
21. add example KB data
22. add demo queries
23. write README with setup and examples
24. add confidence flags and fallback behavior

---

## 11. Rule design principles for V1
Use rules that are easy to inspect and easy to replace later.

### Good rule example
If normalized query contains:
- “农业生产资料投入”
- and “未结清贷款”
Then:
- demand_scenario = `crop_input_purchase`
- constraint_label add `existing_debt_constraint`

### Bad rule example
A single giant mixed rule file that combines retrieval, policy parsing, economics interpretation, and response wording in one place.

Keep rules separated by function.

---

## 12. Evaluation plan for V1
The first version does not need fancy benchmarks.
But it must be testable.

### Minimum evaluation dimensions
1. retrieval relevance
2. evidence correctness
3. parameter extraction correctness
4. response faithfulness to evidence
5. fallback behavior when evidence is weak

### Suggested mini test set
Prepare 20 to 30 hand-written queries covering:
- crop input loans
- livestock loans
- subsidy questions
- cooperative-related eligibility
- renewal / extension questions
- debt not yet repaid
- unsupported / out-of-scope questions

### Suggested metrics
- top-1 retrieval correctness
- top-3 retrieval correctness
- parameter extraction precision
- template response faithfulness check

---

## 13. Current project thinking
This section is for project guidance, not only coding.

### 13.1 What the project is really doing
The system is not just searching files.
It is doing three linked jobs:
- understanding the user’s financing situation from rough language
- locating official evidence in a small policy base
- turning policy text into a constrained, economics-aware interpretation

### 13.2 Why this is appropriate for computational linguistics
This project shows CL ability through concrete language-processing modules:
- text normalization
- lexical mapping
- information retrieval
- extractive evidence selection
- structured slot update
- rule-grounded response generation

This is much more defensible than simply calling a large model and claiming the system understands language.

### 13.3 Why economics matters here
Because the knowledge base is small, the system cannot survive as a pure FAQ engine.
Economics provides structure in the gaps.
Even in V1, economics helps the system distinguish:
- production loan vs consumption-like need
- first-time application vs renewal / extension scenario
- subsidy availability vs hard eligibility block
- short-term cash-flow stress vs longer-term expansion need

---

## 14. Future expansion roadmap
The architecture must leave interfaces for future upgrades.
V1 is the wooden frame.
Future versions can add stronger tools without breaking the frame.

### 14.1 Future CL upgrades
Possible later modules:
- CRF / BiLSTM-CRF entity extraction
- SRL-based event and role parsing
- dependency-based rule enrichment
- intent classifier trained on annotated farmer queries
- hybrid sparse + dense retrieval
- query rewriting model
- contradiction / entailment checker

### 14.2 Future economics upgrades
Possible later modules:
- richer demand-type model
- liquidity-constraint scoring
- renewal / extension risk scoring
- relationship-lending soft information model
- seasonal repayment timing model
- simple farmer cash-flow simulator

### 14.3 Future memory upgrades
Possible later modules:
- time-decay slot memory
- belief-state update
- profile evolution across sessions
- uncertainty-aware user state
- knowledge-gap clustering from failed queries

### 14.4 Future product upgrades
Possible later modules:
- ask-back clarification questions
- evidence comparison across policies
- admin dashboard for missing-knowledge analysis
- data collection form linked to dialogue state
- multilingual / dialect support

---

## 15. Interface rules for future-proofing
To keep upgrades smooth, every module should communicate through structured objects rather than free text.

Examples:
- retriever returns ranked chunks
- extractor returns named parameters
- econ adapter returns scenario and constraint labels
- response builder consumes structured fields

Do not make one module depend on another module’s wording.
Make modules depend on fields, not sentences.

This will allow later replacement of:
- BM25 with hybrid retrieval
- regex extractor with trained extractor
- rule-based demand classifier with statistical classifier
without rewriting the whole system.

---

## 16. Codex tasking instructions
Codex should read and follow this section as the direct build instruction.

### Build objective
Produce a clean, local, runnable V1 rural credit QA system that:
- uses a small official-policy knowledge base
- retrieves relevant paragraphs with BM25 or TF-IDF
- selects supporting sentences
- extracts a few policy parameters with rules
- returns a controlled evidence-grounded answer
- stores simple structured session state

### Coding priorities
1. correctness over cleverness
2. explicit modules over hidden coupling
3. readable rules over dense abstractions
4. evidence grounding over fluent wording
5. stable I/O schemas over short-term convenience

### Avoid
- giant monolithic script
- all logic inside one API handler
- hard-coded demo logic spread everywhere
- silent failure when nothing relevant is found
- policy interpretation without quoting evidence

### Deliverables
At minimum, generate:
- runnable codebase
- requirements file
- example KB chunk file
- synonym config file
- simple API server
- README with setup instructions
- 5 to 10 demo queries
- basic tests

---

## 17. Suggested first README opening paragraph
This repository implements a first-version rural credit QA system for small official-policy knowledge bases. The system is retrieval-first and evidence-grounded. It does not rely on a large language model as the core engine. Instead, it uses explicit text normalization, BM25 / TF-IDF retrieval, sentence-level evidence selection, rule-based parameter extraction, lightweight economics-aware interpretation, and session slot memory. The architecture is intentionally modular so future computational linguistics and quantitative economics components can be attached smoothly.

---

## 18. Final build decision
The first version should be intentionally plain, inspectable, and solid.
A plain iron hammer is better than a gold-colored plastic tool.

For this project, that means:
- simple retrieval
- visible evidence
- controlled response
- small economics layer
- modular architecture

That is the correct V1.
