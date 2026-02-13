# getTestData.py —— 神经医学专项评测版（支持断点续传）

import os
import json
import argparse
import logging
import time
import asyncio
import pandas as pd

from datasets import load_dataset, Dataset
from ragas import evaluate
from ragas.llms import llm_factory

# ✅ 修复 deprecation warning
from ragas.metrics.collections import (
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

import openai

# ================== 基础配置 ==================
OUT_CSV = "medical_agent_eval_details.csv"
PARTIAL_CSV = "medical_agent_eval_details_partial.csv"
CKPT = "getTestData.ckpt.json"  # ✅ 断点文件

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL")

# ✅ 神经医学关键词（扩充版）
NEURO_KEYWORDS = [
    "脑", "神经", "卒中", "中风", "脑梗", "脑出血", "脑血管",
    "头痛", "头晕", "眩晕", "昏迷", "意识",
]

# ================== 日志 ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("RAGAS-Neuro")


# ================== 断点续传工具 ==================
def load_checkpoint():
    """加载断点"""
    if os.path.exists(CKPT):
        try:
            with open(CKPT, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"next_idx": 0, "written": 0}


def save_checkpoint(next_idx, written):
    """保存断点"""
    with open(CKPT, "w", encoding="utf-8") as f:
        json.dump({
            "next_idx": next_idx,
            "written": written,
            "ts": time.time()
        }, f, ensure_ascii=False, indent=2)


# ================== 工具函数 ==================
def safe_text(x):
    if x is None:
        return ""
    if isinstance(x, (list, dict)):
        return json.dumps(x, ensure_ascii=False)
    return str(x).strip()


def is_neuro_case(case):
    """✅ 核心筛选：判断是否为神经医学病例"""
    text = (
            safe_text(case.get('title', '')) +
            safe_text(case.get('description', '')) +
            safe_text(case.get('exam', '')) +
            safe_text(case.get('question', ''))
    ).lower()

    return any(keyword in text for keyword in NEURO_KEYWORDS)


def append_partial_row(row: dict):
    if not os.path.exists(PARTIAL_CSV):
        pd.DataFrame(columns=row.keys()).to_csv(
            PARTIAL_CSV, index=False, encoding="utf-8-sig"
        )
    pd.DataFrame([row]).to_csv(
        PARTIAL_CSV,
        mode="a",
        header=False,
        index=False,
        encoding="utf-8-sig"
    )


def normalize_contexts(contexts):
    """✅ 确保 contexts 是纯文本列表，且不为空"""
    if not contexts:
        logger.warning("⚠️ contexts 为空，使用占位文本")
        return ["未检索到相关神经医学文献"]

    flat = []
    for c in contexts:
        if isinstance(c, dict):
            text = f"{c.get('content', '')} {c.get('text', '')}".strip()
            if text:
                flat.append(text[:500])
        elif isinstance(c, str) and c.strip():
            flat.append(c[:500])

    if not flat:
        return ["未检索到相关神经医学文献"]

    return flat[:5]


# ================== 数据生成 ==================
def build_question(case):
    """✅ 简化问题格式"""
    title = safe_text(case.get('title', ''))
    desc = safe_text(case.get('description', ''))
    question = f"{title} {desc}".strip()
    return question[:300]


def extract_reference(case):
    """✅ 改进版：提取更完整的参考答案"""

    # 1. 尽量提取完整的答案描述
    candidates = []

    # 优先级 1：诊断字段
    for key in ["diagnosis", "final_diagnosis", "诊断", "主要诊断"]:
        if case.get(key):
            candidates.append(safe_text(case.get(key)))

    # 优先级 2：explanation
    if case.get("explanation"):
        candidates.append(safe_text(case.get("explanation")))

    # 优先级 3：answer + option
    if case.get("answer"):
        ans = case["answer"]
        if len(ans) == 1 and ans.isalpha():
            option_text = case.get(f"option_{ans}", "")
            if option_text:
                candidates.append(option_text)
        candidates.append(ans)

    # 优先级 4：其他可能的医学信息
    for key in ["treatment", "management", "治疗", "处理", "建议"]:
        if case.get(key):
            candidates.append(safe_text(case.get(key)))

    # 返回第一个非空的，或拼接所有
    if candidates:
        # 拼接多个候选答案，提高 reference 的完整性
        result = " ".join([c for c in candidates if c])[:300]
        return result if result else "无明确参考答案"

    return "无明确参考答案"


def generate_samples(agent, test_count=5, resume=True, force_restart=False):
    """✅ 生成测试样本（支持断点续传）"""
    logger.info("📦 开始筛选神经医学病例...")

    dataset = load_dataset(
        "FreedomIntelligence/CMB",
        "CMB-Clin",
        split="test"
    )

    # ✅ 断点续传逻辑
    if force_restart:
        for f in [CKPT, PARTIAL_CSV, OUT_CSV]:
            if os.path.exists(f):
                os.remove(f)
                logger.info(f"🗑️ 已删除旧文件: {f}")

    ck = load_checkpoint() if resume else {"next_idx": 0, "written": 0}
    start_idx = int(ck["next_idx"])
    written = int(ck["written"])
    skipped = 0

    logger.info(f"📍 从索引 {start_idx} 继续，已完成 {written} 个样本")

    for idx in range(start_idx, len(dataset)):
        if written >= test_count:
            logger.info(f"✅ 已完成目标数量 {test_count} 个样本")
            break

        case = dataset[idx]

        # ✅ 神经病例筛选
        if not is_neuro_case(case):
            skipped += 1
            save_checkpoint(idx + 1, written)
            continue

        try:
            q = build_question(case)
            logger.info(f"🧠 处理神经病例 {idx}: {q[:50]}...")

            res = agent.run(q)

            if isinstance(res, tuple) and len(res) == 2:
                answer, contexts = res
            else:
                answer = str(res)
                contexts = []
                logger.warning(f"⚠️ Agent 未返回 contexts，样本 {idx}")

            contexts = normalize_contexts(contexts)
            answer = safe_text(answer)[:800]

            row = {
                "question": q,
                "answer": answer,
                "contexts": json.dumps(contexts, ensure_ascii=False),
                "reference": extract_reference(case),
                "dataset_idx": idx,
                "ts": int(time.time())
            }

            append_partial_row(row)
            written += 1
            save_checkpoint(idx + 1, written)
            logger.info(f"✅ 样本 {idx} 完成 (已跳过 {skipped} 个非神经病例)")

        except Exception as e:
            logger.error(f"❌ 样本 {idx} 失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            save_checkpoint(idx + 1, written)  # ✅ 失败也保存断点

    if os.path.exists(PARTIAL_CSV):
        pd.read_csv(PARTIAL_CSV).to_csv(
            OUT_CSV, index=False, encoding="utf-8-sig"
        )
        logger.info(f"✅ 已保存 {written} 条神经医学样本到 {OUT_CSV}")


# ================== RAGAS 评测 ==================
def prepare_for_ragas(df: pd.DataFrame):
    """✅ 严格按 RAGAS 要求格式化数据"""
    df = df.rename(columns={
        "question": "user_input",
        "answer": "response",
        "contexts": "retrieved_contexts",
        "reference": "reference"
    })

    def parse_contexts(x):
        try:
            parsed = json.loads(x) if isinstance(x, str) else x
            if isinstance(parsed, list):
                return [str(item)[:500] for item in parsed if item]
            return ["未检索到相关神经医学文献"]
        except:
            return ["未检索到相关神经医学文献"]

    df["retrieved_contexts"] = df["retrieved_contexts"].apply(parse_contexts)
    df["reference"] = df["reference"].astype(str)

    df["user_input"] = df["user_input"].astype(str).str[:300]
    df["response"] = df["response"].astype(str).str[:800]
    df["reference"] = df["reference"].astype(str).str[:200]

    logger.info("✅ 数据格式化完成，预览:")
    logger.info(df[["user_input", "retrieved_contexts", "reference"]].head(1))

    return Dataset.from_pandas(df)


def run_evaluation(eval_count=5):
    logger.info("⚖️ 开始 RAGAS 评测...")

    if not os.path.exists(OUT_CSV):
        logger.error(f"❌ 未找到数据文件: {OUT_CSV}")
        return

    df = pd.read_csv(OUT_CSV, dtype=str).tail(eval_count)
    dataset = prepare_for_ragas(df)

    # ✅ 创建 OpenAI client
    client = openai.OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE_URL
    )

    # ✅ 使用 llm_factory 创建 LLM
    ragas_llm = llm_factory(
        model="gpt-4o-mini",
        client=client,
        temperature=0,
        max_tokens=8192,
    )

    # ✅ 只使用不需要 embedding 的 metrics
    from ragas.metrics import faithfulness

    metrics = [faithfulness]

    try:
        logger.info("📊 正在计算 Faithfulness 指标（医学答案准确性）...")

        # ✅ 只传 llm，不传 embeddings
        result = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=ragas_llm,
            raise_exceptions=False,
        )

        # ✅ 核心修复：处理列表结果
        result_df = result.to_pandas()
        faithfulness_scores = result_df['faithfulness'].tolist()
        avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else 0
        min_faithfulness = min(faithfulness_scores) if faithfulness_scores else 0
        max_faithfulness = max(faithfulness_scores) if faithfulness_scores else 0

        print("\n" + "=" * 60)
        print("🎯 神经医学 RAGAS 评测结果")
        print("=" * 60)
        print(f"Faithfulness（医学答案准确性）")
        print(f"  • 平均值: {avg_faithfulness:.4f}")
        print(f"  • 最小值: {min_faithfulness:.4f}")
        print(f"  • 最大值: {max_faithfulness:.4f}")
        print("=" * 60)

        print("\n📊 指标解释:")
        print("- Faithfulness 范围: 0.0 ~ 1.0")
        print("  * 0.0-0.3: 回答严重缺乏依据，存在幻觉")
        print("  * 0.3-0.6: 回答部分正确，但有些观点缺乏证据支持")
        print("  * 0.6-0.8: 回答较为准确，大部分基于检索文献")
        print("  * 0.8-1.0: 回答完全基于检索文献，准确可靠")

        # ✅ 判断评估等级
        if avg_faithfulness >= 0.8:
            level = "🟢 优秀"
        elif avg_faithfulness >= 0.6:
            level = "🟡 良好"
        elif avg_faithfulness >= 0.4:
            level = "🟠 需改进"
        else:
            level = "🔴 需严重改进"

        print(f"\n总体评估: {level}")

        # 保存结果
        result_df.to_csv(
            "ragas_neuro_results.csv",
            index=False,
            encoding="utf-8-sig"
        )
        logger.info("✅ 结果已保存到 ragas_neuro_results.csv")

        # 显示详细的逐样本结果
        print("\n" + "=" * 60)
        print("📋 逐样本 Faithfulness 分数详情:")
        print("=" * 60)
        for idx, row in result_df.iterrows():
            score = row['faithfulness']
            if score >= 0.7:
                status = "✅"
            elif score >= 0.4:
                status = "⚠️"
            else:
                status = "❌"
            print(f"{status} 样本 {idx}: {score:.4f}")

    except Exception as e:
        logger.error(f"❌ RAGAS 评测失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

# ================== Main ==================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_count", type=int, default=5, help="需要收集的神经病例数量")
    parser.add_argument("--eval_only", action="store_true", help="仅运行评测")
    parser.add_argument("--resume", action="store_true", help="从断点继续")
    parser.add_argument("--force_restart", action="store_true", help="强制重新开始")
    args = parser.parse_args()

    if not args.eval_only:
        from Agent.qwen.qwenAgent import qwenAgent
        agent = qwenAgent()
        generate_samples(
            agent,
            test_count=args.test_count,
            resume=args.resume,
            force_restart=args.force_restart
        )

    run_evaluation(eval_count=args.test_count)


if __name__ == "__main__":
    main()





# # getTestData.py (Ragas 稳定运行版)
# import os
# import json
# import argparse
# import logging
# import time
# import traceback
# import pandas as pd
# from datasets import load_dataset, Dataset
#
# # 1. 【核心修复】使用最基础的 evaluate 和 metrics 引用，无视警告
# from ragas import evaluate
# from ragas.metrics import (
#     faithfulness,
#     answer_relevancy,
#     context_precision,
#     context_recall,
# )
#
#
# # 2. 【核心修复】使用 Ragas 原生支持的 LLM 和 Embedding 方式
# import openai
# from ragas.llms import llm_factory
# from ragas.embeddings import OpenAIEmbeddings
#
# # ---------------- 配置 ----------------
# OUT_CSV = "medical_agent_eval_details.csv"
# PARTIAL_CSV = "medical_agent_eval_details_partial.csv"
# CKPT = "getTestData.ckpt.json"
#
# DEEPSEEK_API_KEY = os.getenv("DEEPSEEK-API-KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# OPENAI_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL")
#
# # ---------------- 日志配置 ----------------
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# logger = logging.getLogger("MedicalEvaluator")
#
# CSV_PARTIAL_FIELDS = ["question", "answer", "contexts", "reference", "dataset_idx", "ts"]
#
#
# # ---------------- 工具函数 ----------------
# def safe_text(x):
#     if x is None: return ""
#     if isinstance(x, (list, dict)):
#         try:
#             return json.dumps(x, ensure_ascii=False)
#         except:
#             return str(x)
#     return str(x).strip()
#
#
# def load_checkpoint():
#     if os.path.exists(CKPT):
#         try:
#             with open(CKPT, "r", encoding="utf-8") as f:
#                 return json.load(f)
#         except:
#             pass
#     return {"next_idx": 0, "written": 0}
#
#
# def save_checkpoint(next_idx, written):
#     with open(CKPT, "w", encoding="utf-8") as f:
#         json.dump({"next_idx": next_idx, "written": written, "ts": time.time()}, f, ensure_ascii=False, indent=2)
#
#
# def append_partial_row(row, path=PARTIAL_CSV):
#     if not os.path.exists(path):
#         pd.DataFrame(columns=CSV_PARTIAL_FIELDS).to_csv(path, index=False, encoding="utf-8-sig")
#     pd.DataFrame([row]).to_csv(path, mode="a", header=False, index=False, encoding="utf-8-sig")
#
#
# # ---------------- 核心逻辑 ----------------
# def extract_ground_truth(case):
#     """从数据集提取标准答案"""
#     out = []
#     answer_key = case.get("answer", "")
#     if answer_key:
#         if len(answer_key) == 1 and answer_key.isalpha():
#             option_text = case.get(f"option_{answer_key}", "")
#             if option_text: out.append(f"标准答案：{answer_key}. {option_text}")
#         else:
#             out.append(f"标准答案：{answer_key}")
#     explanation = safe_text(case.get("explanation", ""))
#     if explanation: out.append(f"解析：{explanation}")
#     if not out:
#         for key in ("diagnosis", "final_diagnosis", "label", "诊断"):
#             if case.get(key): out.append(safe_text(case.get(key)))
#     return out if out else ["无明确标准答案"]
#
#
# def build_question_from_case(case):
#     title = safe_text(case.get("title", ""))
#     des = safe_text(case.get("description", ""))
#     extras = [safe_text(case.get(k)) for k in ("history", "past_history", "present_illness") if case.get(k)]
#     return f"你是一名神经内科医生，请基于以下病历给出主要诊断、依据及建议：\n\n【标题】{title}\n【详情】{des}\n{' '.join(extras)}"
#
#
# def generate_samples(agent, test_count=3, keywords=None, dataset_name="FreedomIntelligence/CMB", subset="CMB-Clin",
#                      resume=True, force_restart=False):
#     """生成测试样本"""
#     logger.info("开始生成样本...")
#     raw = load_dataset(dataset_name, subset, split="test")
#
#     if force_restart:
#         for f in [CKPT, PARTIAL_CSV, OUT_CSV]:
#             if os.path.exists(f): os.remove(f)
#
#     ck = load_checkpoint() if resume else {"next_idx": 0, "written": 0}
#     start, written, processed = int(ck["next_idx"]), int(ck["written"]), 0
#     keywords = keywords or ["神经", "脑", "卒中", "癫痫", "帕金森"]
#
#     for idx in range(start, len(raw)):
#         if processed >= test_count: break
#         case = raw[idx]
#         blob = safe_text(case.get("title", "")) + safe_text(case.get("description", ""))
#         if not any(k in blob for k in keywords):
#             save_checkpoint(idx + 1, written)
#             continue
#
#         try:
#             res = agent.run(build_question_from_case(case))
#             answer, contexts = (res[0], res[1]) if isinstance(res, tuple) else (res, [])
#
#             row = {
#                 "question": build_question_from_case(case),
#                 "answer": safe_text(answer),
#                 "contexts": json.dumps(contexts, ensure_ascii=False),
#                 "reference": json.dumps(extract_ground_truth(case), ensure_ascii=False),
#                 "dataset_idx": idx,
#                 "ts": int(time.time()),
#             }
#             append_partial_row(row)
#             written += 1
#             processed += 1
#             save_checkpoint(idx + 1, written)
#             logger.info("完成样本 idx=%d", idx)
#         except Exception as e:
#             logger.error("样本 idx=%d 生成失败: %s", idx, e)
#
#     if os.path.exists(PARTIAL_CSV):
#         pd.read_csv(PARTIAL_CSV, dtype=str).to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
#
#
# # ---------------- Ragas 评测 (修复版) ----------------
# def prepare_df_for_ragas(df):
#     """数据格式化"""
#     df_eval = df.copy()
#
#     def parse_list(x):
#         try:
#             return json.loads(x) if isinstance(x, str) else x
#         except:
#             return [x] if x else []
#
#     column_mapping = {
#         "question": "user_input",
#         "answer": "response",
#         "contexts": "retrieved_contexts",
#         "reference": "reference"
#     }
#     df_eval = df_eval.rename(columns=column_mapping)
#
#     # 强制类型转换
#     df_eval["retrieved_contexts"] = df_eval["retrieved_contexts"].apply(parse_list)
#     df_eval["reference"] = df_eval["reference"].apply(lambda x: "\n".join(parse_list(x)))
#
#     return df_eval
#
#
# def run_evaluation(eval_count=None):
#     if not os.path.exists(OUT_CSV):
#         logger.error("找不到数据文件")
#         return
#
#     df_raw = pd.read_csv(OUT_CSV, dtype=str, keep_default_na=False)
#     if eval_count:
#         df_raw = df_raw.tail(eval_count)
#
#     df_prepared = prepare_df_for_ragas(df_raw)
#     ragas_dataset = Dataset.from_pandas(df_prepared)
#
#     # OpenAI client
#     openai_client = openai.OpenAI(
#         api_key=OPENAI_API_KEY,
#         base_url=OPENAI_API_BASE_URL
#     )
#
#     ragas_llm = llm_factory(
#         model="gpt-4o-mini",
#         client=openai_client
#     )
#
#     ragas_emb = OpenAIEmbeddings(
#         client=openai_client,
#         model="text-embedding-3-small"
#     )
#
#     # ✅ 与你当前 Ragas 版本完全匹配的写法
#     metrics = [
#         faithfulness,
#         answer_relevancy,
#         context_precision,
#         context_recall,
#     ]
#
#     logger.info("⚖️ 开始 Ragas 评测...")
#     result = evaluate(
#         dataset=ragas_dataset,
#         metrics=metrics,
#         llm=ragas_llm,
#         embeddings=ragas_emb,
#     )
#
#     print(result)
#     result.to_pandas().to_csv(
#         "ragas_final_results.csv",
#         index=False,
#         encoding="utf-8-sig"
#     )
#
#
#
# # ---------------- Main ----------------
# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--test_count", type=int, default=5)
#     parser.add_argument("--keywords", type=str, default=None)
#     parser.add_argument("--eval_only", action="store_true")
#     args = parser.parse_args()
#
#     if not args.eval_only:
#         from Agent.qwen.qwenAgent import qwenAgent
#         agent = qwenAgent()
#         kw = [k.strip() for k in args.keywords.split(",")] if args.keywords else None
#         generate_samples(agent, test_count=args.test_count, keywords=kw)
#
#     run_evaluation(eval_count=args.test_count)
#
#
# if __name__ == "__main__":
#     main()