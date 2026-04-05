import os
import pandas as pd
from datasets import load_dataset, Dataset
# 【修复 1】修正 ragas 导入拼写 (answer_relevance -> answer_relevancy)
# Ragas v0.1+ 版本中推荐使用 metrics 直接导入
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall

# 【接入真实项目】引入你的 qwenAgent
from Agent.qwen.qwenAgent import qwenAgent


def get_neuro_dataset(count=3):
    print("⏳ 正在拉取 CMB-Clin 神经医学数据...")
    try:
        ds = load_dataset("FreedomIntelligence/CMB", "CMB-Clin", split="test", trust_remote_code=True)
    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        print("💡 提示: 请检查网络连接或 HuggingFace Token 设置")
        return []

    data_list = []
    for item in ds:
        if len(data_list) >= count:
            break

        title = item.get('title', '')
        desc = item.get('description', '')
        question = f"{title}\n{desc}".strip()
        ground_truth = item.get("answer", "")

        if question and ground_truth:
            data_list.append({
                "question": question,
                "ground_truth": ground_truth
            })

    print(f"✅ 已准备 {len(data_list)} 条测试数据")
    return data_list


def main():
    if not os.getenv("QWEN-API-KEY") or not os.getenv("DEEPSEEK-API-KEY"):
        print("⚠️ 警告: 检测到可能缺少 API Key 环境变量，请确保已设置 QWEN-API-KEY 和 DEEPSEEK-API-KEY")

    test_data = get_neuro_dataset(count=2)  # 先跑2条测通
    if not test_data:
        print("❌ 未获取到测试数据，程序退出。")
        return
    print("🤖 正在初始化 QwenAgent...")
    try:
        agent = qwenAgent()
    except Exception as e:
        print(f"❌ Agent 初始化失败: {e}")
        return

    questions = []
    ground_truths = []
    answers = []
    contexts = []

    print("🚀 开始 RAG 评测循环 (这将调用真实 API，请耐心等待)...")

    for i, item in enumerate(test_data):
        q = item["question"]
        gt = item["ground_truth"]

        print(f"\n--- Case {i + 1} ---")
        print(f"Q: {q[:30]}...")

        try:
            full_response, _ = agent.run(q)

            prefix = "\n这是综合诊疗结果：\n"
            generated_answer = full_response.replace(prefix, "").strip()
            generated_answer = generated_answer.replace("这是综合诊疗结果：\n", "").strip()

            retrieved_docs = agent.retriever_engine.search(q, top_k_final=3)
            ctx_list = [doc.page_content for doc in retrieved_docs]

            questions.append(q)
            ground_truths.append(gt)
            answers.append(generated_answer)
            contexts.append(ctx_list)

            print("✅ 成功生成回答与检索上下文")

        except Exception as e:
            print(f"❌ 处理 Case {i + 1} 出错: {e}")
            continue

    if not questions:
        print("❌ 未生成有效数据，退出。")
        return

    data_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    }

    rag_dataset = Dataset.from_dict(data_dict)

    print("\n📊 正在调用 Ragas 计算指标 (evaluator LLM 也会消耗 Token)...")
    try:
        results = evaluate(
            rag_dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ],
        )

        print("\n✅ 评测结果:")
        print(results)

        df = results.to_pandas()
        output_file = "rag_eval_results.csv"
        df.to_csv(output_file, index=False)
        print(f"💾 详细结果已保存至 {output_file}")

    except Exception as e:
        print(f"❌ Ragas 评测计算失败: {e}")
        print(
            "提示: Ragas 默认使用 OpenAI 作为评测模型，请确保环境变量中有 OPENAI_API_KEY，或者是通过 ragas 的 llm 参数配置了其他模型。")


if __name__ == "__main__":
    main()

