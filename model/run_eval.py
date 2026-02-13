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
    # 【修复 2】修正 config 名称 'clin' -> 'CMB-Clin'
    # trust_remote_code=True 有助于执行 HuggingFace 数据集的加载脚本
    try:
        ds = load_dataset("FreedomIntelligence/CMB", "CMB-Clin", split="test", trust_remote_code=True)
    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        print("💡 提示: 请检查网络连接或 HuggingFace Token 设置")
        return []

    data_list = []
    # 遍历数据集提取 Question 和 Ground Truth
    for item in ds:
        if len(data_list) >= count:
            break

        # CMB 数据集结构通常包含 'title', 'description'
        title = item.get('title', '')
        desc = item.get('description', '')
        # 拼接作为完整的用户问题
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
    # 0. 环境变量检查
    # 你的 qwenAgent 强依赖这两个环境变量，请确保已设置
    if not os.getenv("QWEN-API-KEY") or not os.getenv("DEEPSEEK-API-KEY"):
        print("⚠️ 警告: 检测到可能缺少 API Key 环境变量，请确保已设置 QWEN-API-KEY 和 DEEPSEEK-API-KEY")

    # 1. 获取测试数据
    test_data = get_neuro_dataset(count=2)  # 先跑2条测通
    if not test_data:
        print("❌ 未获取到测试数据，程序退出。")
        return

    # 2. 初始化你的真实 Agent
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
            # 3. 【真实生成】调用 Agent 获取回答
            # agent.run 返回 tuple: (带有前缀的回答, 总结)
            full_response, _ = agent.run(q)

            # 【关键】清理 agent.run 中硬编码的前缀，否则会影响 Answer Relevancy
            prefix = "\n这是综合诊疗结果：\n"
            generated_answer = full_response.replace(prefix, "").strip()
            # 再次防御性清理，防止前缀只有部分匹配
            generated_answer = generated_answer.replace("这是综合诊疗结果：\n", "").strip()

            # 4. 【真实检索】获取检索到的文档片段 (Contexts)
            # Ragas 需要知道生成答案时参考了哪些文档。
            # 我们手动调用 agent 中的 retriever_engine 来模拟这个过程
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

    # 5. 构建 Ragas 数据集
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

    # 6. 计算指标
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

        # 7. 保存结果
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

