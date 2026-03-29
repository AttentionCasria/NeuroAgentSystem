"""
Qwen VL 多模态模型可用性测试脚本（一次性使用，测试后手动删除）
使用 Base64 编码的纯色图片，避免依赖外部图片 URL
"""

import base64
import io
from PIL import Image
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import HumanMessage

DASHSCOPE_API_KEY = "sk-26c638a2564d4b44833e4866365a56c9"
TEST_MODELS = ["qwen-vl-max", "qwen-vl-plus", "qwen2.5-vl-72b-instruct"]

# 生成一张 100x100 红色纯色测试图片
img = Image.new('RGB', (100, 100), color='red')
buffer = io.BytesIO()
img.save(buffer, format='PNG')
base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
IMAGE_DATA_URL = f"data:image/png;base64,{base64_image}"

def test_model(model_name: str) -> tuple[bool, str]:
    """测试单个 VL 模型，返回 (是否成功, 结果或错误信息)"""
    try:
        llm = ChatTongyi(model=model_name, dashscope_api_key=DASHSCOPE_API_KEY, streaming=False)
        message = HumanMessage(content=[
            {"type": "image_url", "image_url": {"url": IMAGE_DATA_URL}},
            {"type": "text",      "text": "请描述这张图片的颜色"},
        ])
        resp = llm.invoke([message])
        content = resp.content if hasattr(resp, "content") else str(resp)
        return True, content[:200]  # 只截取前200字，够验证即可
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 60)
    print("Qwen VL 模型可用性测试")
    print("测试图片：Base64 编码红色纯色图片（100x100）")
    print("=" * 60)

    results = {}
    first_success = None

    for model in TEST_MODELS:
        print(f"\n▶ 测试 {model} ...")
        ok, msg = test_model(model)
        results[model] = ok
        if ok:
            print(f"  ✅ 可用")
            print(f"  回复摘要：{msg}")
            if first_success is None:
                first_success = model
        else:
            print(f"  ❌ 不可用：{msg}")

    print("\n" + "=" * 60)
    print("测试汇总：")
    for model, ok in results.items():
        status = "✅ 可用" if ok else "❌ 不可用"
        print(f"  {status}  {model}")

    if first_success:
        print(f"\n建议在 vision_service.py 中使用：{first_success}")
    else:
        print("\n⚠️ 所有模型均不可用，请确认 DASHSCOPE_API_KEY 已设置且已开通 VL 模型权限")
    print("=" * 60)


if __name__ == "__main__":
    main()
