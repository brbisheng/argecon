

---

## 给 Codex 的补充指令：数据处理模块要按不稳定数据形态设计 LONGER VERSION

当前数据源不是干净统一的数据集，而是**地区文件夹 + Word 文档为主**，后期可能逐步加入 `txt`、`md`、`pdf`、图片。
请你在实现数据处理模块时，不要按“单一格式、单一目录、一次性导入”的假设来写，而要按**多格式、分地区、可扩展、可容错**来设计。

### 一、当前已知数据形态

初期主要是：

* 顶层按地区分文件夹
* 每个地区文件夹内主要是 Word 文档
* 后期可能加入：

  * txt
  * md
  * pdf
  * 图片（扫描件、截图、拍照文件）

### 二、实现原则

请按下面原则实现 ingestion / preprocessing 模块：

#### 1. 统一入口，分格式解析

设计一个统一的数据导入入口，例如：

* `scan_data_sources()`
* `load_documents()`
* `parse_document()`

其中 `parse_document()` 内部再按文件后缀分发到不同 parser：

* `parse_docx`
* `parse_txt`
* `parse_md`
* `parse_pdf`
* `parse_image`

即使初期只有 `docx` 真正启用，也要先把接口留好，不要把 Word 解析逻辑写死在主流程里。

---

#### 2. 允许“部分支持”，不要因为一种格式失败就整个中断

系统必须做到：

* 某个文件解析失败，只记录错误并跳过
* 某种格式暂时未完全支持，也不要影响其他文件处理
* 最终输出 ingestion report，说明：

  * 成功解析多少文件
  * 跳过多少文件
  * 哪些失败
  * 失败原因是什么

不要写成“只要一个 pdf 出错，整个索引过程全崩”。

---

#### 3. 每个文档都要保留强 metadata

无论什么格式，解析后都要转成统一中间结构，并尽量保留这些字段：

* `doc_id`
* `region`
* `source_path`
* `file_name`
* `file_type`
* `title`
* `raw_text`
* `paragraphs`
* `source_format_confidence`
* `parse_status`
* `parse_error`
* `created_at` 或文件时间戳（若可得）
* `ingestion_time`

重点是：
以后检索和展示时，要能知道这段文字来自哪个地区、哪个文件、什么格式、解析是否可靠。

---

#### 4. 地区信息不要只靠人工输入，优先从目录自动继承

因为当前数据主要是“地区文件夹 + 文档”，所以系统应优先从目录层级自动提取地区：

例如：

`data/河北/xx政策.docx`
`data/湖北/某县贷款办法.docx`

则自动把 `河北`、`湖北` 写入 metadata 的 `region` 字段。

同时保留手动覆盖接口，因为以后可能出现：

* 多级目录
* 县名 / 市名 / 省名混杂
* 文件被放错地方

所以要支持：

* 自动推断 region
* 手动映射 region
* region 标准化表

---

#### 5. 不要把“文件”和“文本块”混成一层

请区分两层对象：

**Document level**

* 原始文件级别的信息

**Chunk level**

* 切分后的段落 / 文本块信息

也就是先有 document，再从 document 切成多个 chunks。
每个 chunk 必须能回溯到原 document。

chunk 至少保留：

* `chunk_id`
* `doc_id`
* `region`
* `chunk_text`
* `chunk_index`
* `section_title`（若可提取）
* `page_no`（若 PDF 可提取）
* `paragraph_range`

---

#### 6. 切块逻辑不要只适配 Word

虽然初期主要是 docx，但 chunking 逻辑必须尽量格式无关。
建议优先按“自然段 / 标题 / 句群”切块，而不是写死成 Word 段落对象逻辑。

目标是以后接入 txt、md、pdf 时，只要能抽出纯文本和粗略结构，就能复用同一套 chunking。

---

#### 7. PDF 和图片先留接口，不要求第一版完美

第一版不需要把 PDF 和图片处理做到很强，但请先预留：

* `parse_pdf()`：先做可提取文本 PDF
* `parse_image()`：先做 stub / placeholder，后面再接 OCR

也就是说：

* 先支持“有文本层的 PDF”
* 扫描 PDF / 图片先记录为“暂未处理”或“需要 OCR”
* 不要假装已经支持完整 OCR

这样更稳，也更诚实。

---

#### 8. 对文本质量做标记，不要默认解析结果可信

后期会遇到这些问题：

* PDF 提取出来的文字顺序乱
* OCR 文本缺字
* 表格被打碎
* 标题和正文混在一起

所以请在中间结构里预留文本质量字段，例如：

* `text_quality_flag`
* `needs_manual_review`
* `is_scanned_like`
* `ocr_needed`

以后检索时可以用这些字段做过滤或降权。

---

#### 9. 构建可重复运行的 ingestion pipeline

不要写成一次性脚本。
要支持反复运行，并尽量做到：

* 新增文件可以增量导入
* 已处理文件可以跳过或重建
* 文档内容变化后可以重新索引
* 生成 manifest / index 文件，记录当前语料状态

建议至少有：

* `manifest.jsonl`
* `documents.jsonl`
* `chunks.jsonl`
* `ingestion_report.json`

---

#### 10. 错误日志必须清楚

因为数据会很杂，最怕 silent failure。
请输出清楚的日志，例如：

* 哪个文件成功
* 哪个文件失败
* 为什么失败
* 哪些文件为空文本
* 哪些文件疑似扫描件
* 哪些文件 region 无法识别

日志不要只写一句“processing failed”。

---

## 三、你现在可以优先这样实现格式支持顺序

请按下面优先级实现，不要一开始平均用力：

### 第一优先级

* docx
* txt
* md

### 第二优先级

* 可提取文本的 pdf

### 第三优先级

* 图片
* 扫描型 pdf
* OCR 流程

这样更符合当前数据现实。

---

## 四、第一版交付要求

请先完成一个稳健的 ingestion 模块，要求：

1. 能扫描地区文件夹
2. 能解析 docx 为统一 document 结构
3. 能抽取 region metadata
4. 能切块并生成 chunk 数据
5. 能输出 manifest 和 ingestion report
6. 能预留 txt / md / pdf / image parser 接口
7. 某个文件失败时不影响整体流程

---

## 五、代码设计要求

请尽量做到：

* parser registry / dispatcher 设计
* 文档对象和 chunk 对象分层
* 配置文件控制输入目录、支持格式、是否递归扫描
* 模块化，不要把扫描、解析、切块、索引写成一个大函数
* 对未来 OCR、PDF、metadata enrichment 留接口

---

## 六、一句最核心的要求

请把数据处理模块写成一个**面向不稳定真实文档环境**的 ingestion pipeline，而不是面向干净 benchmark 数据集的 demo parser。

---






--- SHORTER VERSION 

补充要求：数据处理模块必须按“真实杂乱文档环境”设计，不要按单一干净数据集写死。

当前数据现状：
- 初期主要是：地区文件夹 + docx
- 后期可能加入：txt、md、pdf、图片
- 数据目录和文件命名未来可能不完全规范

请按以下要求实现 ingestion pipeline：

1. 用统一入口扫描和导入数据
- 例如：scan -> parse -> normalize -> chunk -> save
- 不要把 docx 逻辑写死在主流程里
- 采用 parser dispatcher / registry 结构
- 至少预留：
  - parse_docx
  - parse_txt
  - parse_md
  - parse_pdf
  - parse_image

2. 第一版重点支持：
- docx
- txt
- md
- 可提取文本的 pdf 可先做基础支持
- 图片 / 扫描 pdf 先预留接口，不要求第一版完整 OCR

3. 某个文件失败时不要让整个流程中断
- 单文件失败应记录错误并跳过
- 最终输出 ingestion report，包含：
  - 成功文件数
  - 失败文件数
  - 失败文件路径
  - 失败原因
  - 空文本文件
  - 疑似需要 OCR 的文件

4. 自动从目录继承 region metadata
- 例如 data/河北/xx.docx -> region=河北
- 同时保留手动映射和标准化接口，避免目录混乱时失控

5. 文档层和 chunk 层必须分开
- document 保存原始文件级 metadata
- chunk 保存切块后的文本
- 每个 chunk 必须能回溯到原 document

6. 所有文档统一转成标准中间结构，至少包含：
- doc_id
- region
- source_path
- file_name
- file_type
- title
- raw_text
- paragraphs
- parse_status
- parse_error
- ingestion_time
- text_quality_flag
- needs_manual_review

7. chunk 至少包含：
- chunk_id
- doc_id
- region
- chunk_text
- chunk_index
- section_title（若可提取）
- page_no（若可提取）
- paragraph_range

8. chunking 逻辑不要只适配 Word
- 尽量按自然段 / 标题 / 句群切块
- 让 txt、md、pdf 后续能复用同一套 chunk pipeline

9. 需要可重复运行
- 支持重复执行
- 支持新增文件增量导入
- 支持重建索引
- 输出：
  - manifest.jsonl
  - documents.jsonl
  - chunks.jsonl
  - ingestion_report.json

10. 代码结构不要写成一个大脚本
建议拆成模块：
- scanner
- parsers
- normalizer
- chunker
- manifest writer
- logger / report

第一版交付标准：
- 能扫描地区文件夹
- 能解析 docx
- 能生成 document / chunk 标准结构
- 能自动抽 region
- 能输出 manifest 和 report
- 能预留 txt / md / pdf / image 扩展接口
- 单文件报错不影响整体流程

一句话原则：
把 ingestion 写成“面向未来多格式真实文档”的稳健管道，而不是只为当前 docx demo 临时写通。


如果你愿意，我可以继续帮你把上面这段再压成一个**更短、更像工程 ticket 的版本**，方便你直接贴给 Codex。
