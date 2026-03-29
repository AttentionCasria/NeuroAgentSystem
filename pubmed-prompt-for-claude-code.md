# 任务：为脑卒中辅诊系统集成 PubMed 论文检索功能

> **⚠️ 工作模式：先通读代码 → 和我讨论方案 → 确认后再动手写代码。不要跳过讨论环节。**

---

## 一、项目背景

这是一个三甲医院神经内科的 AI 辅诊系统（Synapse MD），采用三层架构：

```
Python/FastAPI（模型层）→ Java/Spring WebFlux（中间层）→ Vue 3（前端）
```

核心工作流：医生输入患者信息 → AI 做意图分类 → 病例分析 → 并行证据检索（向量库）→ Proposer/Critic 推理 → 流式生成报告（SSE）。

现在要新增一个功能：**在 AI 回复的同时，自动检索 PubMed 上与当前问诊相关的最新论文，在前端侧边栏展示（标题 + 摘要 + 期刊名 + PubMed 链接）**。

---

## 二、请先通读以下文件，理解现有架构

### 必读文件（请逐个打开阅读，不要跳过）

**Python 后端：**
1. `Agent/qwen/qwen_agent.py` — 核心推理管线
   - 重点关注：`_run_clinical_reasoning_core` 方法的事件 yield 流程
   - 重点关注：`_node_analysis` 方法输出的 `clinical_questions`（这是论文检索的关键词来源）
   - 重点关注：`_unified_analysis` 方法的 JSON 输出结构
   - 重点关注：`run_clinical_reasoning` 方法的 `TokenAggregator` 包装层

2. `Agent/qwen/qwen_assistant.py` — 流式报告生成
   - 重点关注：`stream_final_report` 和 `stream_fast_response` 的 async generator 模式

3. `Agent/qwen/medical_agent.py` — 医学检索 Agent
   - 重点关注：`fast_retrieve` 和 `_search_with_retry` 的重试机制（论文检索也需要类似的容错）

4. `makeData/retrieve.py`（如果存在）— 统一检索引擎，了解现有的检索架构

5. `config/config_loader.py`（如果存在）— 了解 PromptManager 和 ReportTemplateManager 的加载机制

6. SSE 端点文件（可能在 `routes/` 或 `main.py` 中）— 找到 `/streamingQues` 对应的 FastAPI 路由，了解 SSE 事件是如何序列化和发送的

**Java 中间层：**
7. 找到 SSE 转发的 Controller（搜索 `streamingQues` 或 `SSE` 或 `Flux`）
   - 了解中间层如何消费 Python SSE 并转发给前端
   - 确认是否有事件过滤/转换逻辑（新增的 `papers` 事件需要被透传）

**Vue 前端：**
8. 找到聊天主组件（可能叫 `ChatWorkspace.vue` 或 `ChatView.vue`）
   - 重点关注：SSE 消费逻辑（`fetch` + `ReadableStream` 解析部分）
   - 重点关注：`chunk` / `thinking` / `done` 等事件类型的处理分支
   - 重点关注：右侧 `.sync-card` 区域的结构（论文侧边栏将放在这里或与之并列）

9. 找到 SSE 工具函数（可能是 `useSSE.js` / `api/stream.js` / `composables/` 下的文件）
   - 了解 SSE 回调的注册方式（`onChunk`、`onThinking`、`onDone` 等）

10. `src/` 目录结构 — 了解项目的文件组织方式（组件在哪、composables 在哪、API 封装在哪）

---

## 三、通读代码后，请和我讨论以下问题

读完代码后，**不要直接开始写代码**，请先回答以下问题，和我对齐方案：

### 3.1 架构确认

1. **SSE 事件流**：请描述你看到的完整 SSE 事件链路。从 Python 的 `yield {"type": "chunk", ...}` 到前端渲染，中间经过了哪些环节？有没有任何地方会过滤或转换事件类型？（如果新增 `type: "papers"` 事件，它能不能不改中间层就透传到前端？）

2. **关键词来源**：`_node_analysis` → `_unified_analysis` 输出的 `clinical_questions` 具体长什么样？给我看一个你在代码中能推断出的示例。这些关键词是中文的，PubMed 需要英文——你打算怎么处理翻译？

3. **异步集成点**：你认为 PubMed 检索应该在推理管线的哪个位置发起？请说明理由。需要确保：
   - 不阻塞主管线（报告生成不能等论文检索）
   - 关键词质量够高（不能用原始用户输入）
   - 有超时兜底（PubMed 挂了不影响主流程）

4. **前端侧边栏位置**：你看到的右侧面板（`.sync-card` 或类似区域）现在是什么内容？论文列表放在哪里最合适？是新增一个 tab，还是在现有面板下方加一个折叠区？

### 3.2 技术选型确认

5. **PubMed API 调用方式**：我倾向于新建一个 `services/pubmed_service.py`，用 `httpx.AsyncClient` 异步调用 PubMed E-utilities（`esearch` + `efetch`），你觉得合适吗？还是有更好的方案？

6. **关键词翻译**：用 `llm_fast`（也就是 `self.llm_critic`）做中文→英文 MeSH 术语的翻译，还是用一个轻量的本地映射表？前者灵活但多一次 LLM 调用（约 0.5-1s），后者快但覆盖面窄。

7. **证据等级过滤**：PubMed 返回的论文有 `PublicationType` 字段（如 `Randomized Controlled Trial`、`Meta-Analysis`、`Case Reports` 等）。是否需要按证据等级排序？（指南 > Meta-Analysis > RCT > 普通综述 > Case Report）

8. **新增依赖**：Python 侧我计划用 `httpx`（异步 HTTP），前端侧可能不需要新增依赖。请确认项目现有的 Python 依赖管理方式（`requirements.txt` / `pyproject.toml` / `poetry`？）和是否已安装 `httpx`。

### 3.3 风险确认

9. **数据隐私**：翻译关键词时，输入给 LLM 的内容可能包含从病例中提取的临床问题（如"72岁男性房颤合并急性缺血性卒中的溶栓指征"）。这里面虽然没有姓名，但有年龄性别等特征。你在代码里看到有没有脱敏处理的逻辑？如果没有，翻译提示词里是否需要额外指示"只提取疾病术语，不包含患者特征"？

10. **PubMed 请求频率**：当多个医生同时使用系统时，PubMed API 的限速是 3 req/s（无 key）或 10 req/s（有 key）。你觉得需要加请求队列和缓存吗？还是现阶段用户量不大可以先不管？

---

## 四、实现方案概要（供讨论参考，不是最终方案）

以下是我预想的方案框架，**请在讨论环节指出你觉得不合适的地方**：

### 4.1 新建文件

```
services/pubmed_service.py     # PubMed E-utilities 封装（esearch + efetch + XML 解析）
```

### 4.2 修改文件

```
Agent/qwen/qwen_agent.py      # 在推理管线中集成 PubMed 检索
                                #   - __init__ 中初始化 PubMedService
                                #   - 新增 _fetch_pubmed_papers() 方法
                                #   - 在 _run_clinical_reasoning_core 中 asyncio.create_task 异步调用
                                #   - 在合适时机 yield {"type": "papers", "content": [...]}

src/???/ChatWorkspace.vue      # 前端 SSE 消费层增加 papers 事件处理
src/components/PapersSidebar.vue  # 新建论文侧边栏组件
src/???/sseClient.js           # SSE 工具函数增加 onPapers 回调
```

### 4.3 SSE 新增事件类型

```json
{
    "type": "papers",
    "content": [
        {
            "pmid": "38234567",
            "title": "Endovascular Thrombectomy for Acute Ischemic Stroke...",
            "abstract": "BACKGROUND: Extended time window...(截断至500字)",
            "authors": "Smith WS, Lev MH, et al.",
            "journal": "New England Journal of Medicine",
            "pub_date": "2025 Mar",
            "url": "https://pubmed.ncbi.nlm.nih.gov/38234567/",
            "pub_type": ["Randomized Controlled Trial"]
        }
    ]
}
```

### 4.4 PubMed API 调用流程

```
_node_analysis 完成
  → 拿到 clinical_questions（中文）
  → asyncio.create_task:
      → llm_fast 翻译为英文 MeSH 查询
      → PubMed esearch（拿 PMID 列表，限最近 3 年，最多 5 篇）
      → PubMed efetch（拿标题/摘要/作者/期刊/日期）
      → 按证据等级排序
  → 主管线继续执行 retrieve → reason → report
  → 在 stream_final_report 之前 await pubmed_task（8s 超时）
  → yield {"type": "papers", ...}
```

### 4.5 PubMed API 参考

```
# 搜索 — 返回 PMID 列表
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
    ?db=pubmed
    &term=acute+ischemic+stroke+thrombectomy
    &retmax=10
    &sort=relevance
    &retmode=json
    &datetype=pdat
    &reldate=1095          # 最近 3 年
    &tool=synapse_md
    &email=项目联系邮箱

# 获取详情 — 返回 XML（需要解析）
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
    ?db=pubmed
    &id=38234567,38234568,38234569
    &rettype=xml
    &retmode=xml

# 限速：无 key = 3 req/s，有 key = 10 req/s
# API key 免费申请：https://www.ncbi.nlm.nih.gov/account/settings/
```

---

## 五、版权与合规约束（已确认，必须遵守）

1. **PubMed 摘要可以展示** — NLM 公开数据，通过 E-utilities 检索并展示标题+摘要是允许的
2. **绝不碰论文全文** — 仅展示标题、摘要（截断至 500 字）和 PubMed 跳转链接
3. **标注数据来源** — 前端需标注 "数据来源: PubMed, U.S. National Library of Medicine"
4. **API 请求带标识** — 所有 PubMed 请求必须包含 `tool=synapse_md` 和 `email` 参数
5. **遵守限速** — 无 API key 不超过 3 req/s，有 key 不超过 10 req/s

---

## 六、前端侧边栏设计要求

论文卡片需要包含以下元素：
- **期刊名**（醒目位置，让医生一眼看到来源权威性）
- **标题**（可点击，新标签页打开 PubMed 链接）
- **作者 + 日期**（灰色小字，一行）
- **证据等级标签**（彩色 pill：红色 = 指南/Meta-Analysis，黄色 = RCT，灰色 = 其他）
- **摘要**（默认折叠，点击展开/收起）
- 状态：加载中 / 空状态 / 错误状态
- 底部免责声明："文献仅供参考，请结合临床判断"
- 使用项目现有的 CSS 变量，兼容深色模式

---

## 七、工作流程

```
Step 1: 通读第二节列出的所有文件
         ↓
Step 2: 回答第三节的 10 个讨论问题（不要写代码）
         ↓
Step 3: 等我确认方案（我可能会调整某些决策）
         ↓
Step 4: 我确认后，开始编码，按以下顺序：
         4a. pubmed_service.py（可独立测试）
         4b. qwen_agent.py 集成（后端完整可用）
         4c. 前端 SSE 消费 + PapersSidebar.vue
         ↓
Step 5: 给出测试方法（如何验证论文检索正常工作）
```

**在 Step 2 完成之前，不要写任何实现代码。**
