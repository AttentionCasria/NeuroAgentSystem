#!/usr/bin/env python3
# scripts/fill_test_results.py
#
# 自动调用本地模型接口，把每道测试题的【调优后】区块填充完整。
# 只填写"回答摘要"仍为空的题目，已填写的跳过。
#
# 用法：
#   python scripts/fill_test_results.py
#   python scripts/fill_test_results.py --url http://1.2.3.4:8000 --only T1-1 T2-3
#   python scripts/fill_test_results.py --dry-run   # 只打印不写文件

import argparse
import datetime
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import jwt          # pip install PyJWT
import requests     # pip install requests

# ─────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────
REPO_ROOT   = Path(__file__).parent.parent
MD_FILE     = REPO_ROOT / "AI对话效果测试用例集.md"
API_URL     = "http://localhost:8000/model/get_result"
SECRET_KEY  = "your-secret-key-here"   # 与 main.py 默认值一致，生产环境请改为环境变量
ALGORITHM   = "HS256"
REPORT_MODE = "emergency"
SHOW_THINKING = False
STREAM_TIMEOUT = 120   # 每题最长等待秒数


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

def make_token() -> str:
    """生成一个永不过期的测试 JWT token。"""
    payload = {"sub": "test-script", "iat": int(time.time())}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def current_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def call_model(question: str, token: str) -> str:
    """
    调用 SSE 流式接口，收集所有 chunk 后返回完整回答文本。
    遇到 error 事件抛出异常。
    """
    payload = {
        "question": question,
        "round": 2,
        "all_info": "",
        "token": token,
        "report_mode": REPORT_MODE,
        "show_thinking": SHOW_THINKING,
        "images": [],
    }

    parts = []
    with requests.post(API_URL, json=payload, stream=True, timeout=STREAM_TIMEOUT) as resp:
        resp.raise_for_status()
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            etype = event.get("type", "")
            if etype == "chunk":
                parts.append(event.get("content", ""))
            elif etype == "result":
                parts.append(event.get("content", ""))
            elif etype == "done":
                # done.result 是完整文本，优先使用（避免 chunk 拼接漏字）
                full = event.get("result", "").strip()
                if full:
                    return full
                break
            elif etype == "error":
                raise RuntimeError(f"模型返回错误：{event.get('content') or event.get('message')}")

    return "".join(parts).strip()


# ─────────────────────────────────────────────
# Markdown 解析 & 回写
# ─────────────────────────────────────────────

# 匹配一道题：从 ### Tx-y（后跟可选标题文字）到下一个 ### Tx-y 或文档末尾
CASE_PATTERN = re.compile(
    r"(### (T\d+-\d+)[^\n]*\n.*?)"    # group(1)=整道题内容  group(2)=题号
    r"(?=\n### T\d+-\d+[^\n]*\n|\Z)",
    re.DOTALL
)

# 从题目内容里提取提示词（代码块里第一段）
PROMPT_PATTERN = re.compile(
    r"\*\*提示词：\*\*\n```\n(.*?)\n```",
    re.DOTALL
)

# 匹配【调优后】区块内容（代码块）
AFTER_BLOCK_PATTERN = re.compile(
    r"(\*\*【调优后】\*\*\n```\n)"    # group(1)=区块头
    r"(.*?)"                            # group(2)=区块内容
    r"(\n```)",                         # group(3)=区块尾
    re.DOTALL
)

# 判断"回答摘要："后面是否有内容（空行不算）
SUMMARY_EMPTY = re.compile(r"回答摘要：\s*\n\s*\n\s*\n?\s*评分：")


def is_after_empty(block_content: str) -> bool:
    return bool(SUMMARY_EMPTY.search(block_content))


def fill_after_block(block_content: str, answer: str, commit: str, today: str) -> str:
    """把 answer 填入调优后区块，保持其他字段不变。"""
    # 替换 日期：、版本/Commit：、回答摘要：
    result = re.sub(r"(日期：)[^\n]*", rf"\g<1>{today}", block_content)
    result = re.sub(r"(版本/Commit：)[^\n]*", rf"\g<1>{commit}", result)
    # 回答摘要：后面到 评分：之前，替换为 answer
    result = re.sub(
        r"(回答摘要：)\s*\n(.*?)(评分：)",
        lambda m: f"{m.group(1)}\n{answer}\n\n\n{m.group(3)}",
        result,
        flags=re.DOTALL
    )
    return result


def process(md_text: str, only: list, dry_run: bool, token: str, commit: str) -> str:
    today = datetime.date.today().isoformat()
    output = md_text

    for m in CASE_PATTERN.finditer(md_text):
        case_id   = m.group(2)          # 如 T1-1
        case_body = m.group(1)

        if only and case_id not in only:
            continue

        # 提取提示词
        pm = PROMPT_PATTERN.search(case_body)
        if not pm:
            print(f"[跳过] {case_id}：未找到提示词")
            continue
        question = pm.group(1).strip()

        # 找【调优后】区块
        am = AFTER_BLOCK_PATTERN.search(case_body)
        if not am:
            print(f"[跳过] {case_id}：未找到【调优后】区块")
            continue

        block_content = am.group(2)

        if not is_after_empty(block_content):
            print(f"[跳过] {case_id}：调优后已有内容")
            continue

        print(f"\n{'='*50}")
        print(f"[处理] {case_id}")
        print(f"[问题] {question[:80]}{'...' if len(question) > 80 else ''}")

        if dry_run:
            print("[dry-run] 跳过 API 调用")
            continue

        try:
            answer = call_model(question, token)
            print(f"[回答] {answer[:120]}{'...' if len(answer) > 120 else ''}")
        except Exception as e:
            print(f"[错误] {case_id} 调用失败：{e}")
            continue

        # 构造新的区块内容
        new_block_content = fill_after_block(block_content, answer, commit, today)

        # 替换到原文中：只替换该题范围内的【调优后】区块
        old_after = am.group(1) + am.group(2) + am.group(3)
        new_after = am.group(1) + new_block_content + am.group(3)
        # 精准替换（只替换第一次在 case_body 范围内出现的）
        new_case_body = case_body.replace(old_after, new_after, 1)
        output = output.replace(case_body, new_case_body, 1)

        print(f"[完成] {case_id} ✅")
        time.sleep(1)  # 避免请求过于密集

    return output


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

def main():
    global API_URL, SECRET_KEY  # 允许命令行参数覆盖模块级配置

    parser = argparse.ArgumentParser(description="自动填写测试用例集调优后结果")
    parser.add_argument("--url",      default=API_URL,    help="模型 API 地址")
    parser.add_argument("--secret",   default=SECRET_KEY, help="JWT secret key")
    parser.add_argument("--only",     nargs="*",          help="只处理指定题号，如 T1-1 T2-3")
    parser.add_argument("--dry-run",  action="store_true",help="只解析不调用接口")
    parser.add_argument("--file",     default=str(MD_FILE),help="测试用例集 md 文件路径")
    args = parser.parse_args()

    API_URL    = args.url
    SECRET_KEY = args.secret
    md_path    = Path(args.file)

    if not md_path.exists():
        print(f"错误：文件不存在 {md_path}", file=sys.stderr)
        sys.exit(1)

    md_text = md_path.read_text(encoding="utf-8")
    token   = make_token()
    commit  = current_commit()

    print(f"文件：{md_path}")
    print(f"Commit：{commit}")
    print(f"API：{API_URL}")
    print(f"dry-run：{args.dry_run}")
    print(f"only：{args.only or '全部'}")

    new_text = process(md_text, args.only or [], args.dry_run, token, commit)

    if not args.dry_run and new_text != md_text:
        md_path.write_text(new_text, encoding="utf-8")
        print(f"\n✅ 已写入 {md_path}")
    elif args.dry_run:
        print("\n[dry-run 完成，未修改文件]")
    else:
        print("\n[无变更]")


if __name__ == "__main__":
    main()
