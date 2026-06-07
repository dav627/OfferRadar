#!/usr/bin/env python3
"""
LLM 分析模块
使用大模型对抓取的岗位信息进行智能分析：
1. 岗位与个人技能的匹配度评分
2. JD 关键信息提取
3. 每日播报的自然语言总结

支持任何兼容 OpenAI 格式的 API（DeepSeek / OpenAI / Zhipu / Moonshot 等）
"""

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from core import PROJECT_ROOT, DATA_DIR
from core import config as config_loader

PROFILE = """
求职方向：LLM应用算法工程师（2027届校招）
核心技能：
- RLHF/DPO/GRPO/SDPO 偏好对齐训练（有美团实习实战经验）
- RAG 生成质量优化（PPO+奖励模型）
- SFT/LoRA 微调（Qwen/DeepSeek 系列，MoE 架构训练加速）
- Multi-Agent 路由优化（UCB+GNN）
- 搜索增强推理（GRPO+Tool Use）
- 熟悉 VERL、LLaMA-Factory、ms-swift、Megatron 框架
不匹配方向：多模态、计算机视觉、语音、基座模型预训练
"""


def _call_llm(prompt: str, system: str = "") -> str:
    cfg = config_loader.get_llm_config()
    if not cfg["api_key"]:
        return ""

    proxy = config_loader.get_proxy()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    data = json.dumps({
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 2000,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{cfg['base_url']}/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
    )

    if proxy.get("https"):
        from urllib.request import ProxyHandler, build_opener
        opener = build_opener(ProxyHandler({"https": proxy["https"], "http": proxy.get("http", "")}))
    else:
        from urllib.request import build_opener
        opener = build_opener()

    try:
        with opener.open(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[WARN] LLM 调用失败: {e}")
        return ""


def analyze_jobs(jobs: list) -> list:
    """对抓取的岗位列表进行智能分析，返回带评分的结果"""
    cfg = config_loader.get_llm_config()
    if not cfg["api_key"]:
        print("[INFO] 未配置 LLM API，跳过智能分析")
        return jobs

    # Batch analyze to save API calls
    job_text = "\n".join(
        f"{i+1}. [{j.get('company','')}] {j.get('title','')} | {j.get('department','')} | {j.get('location','')}"
        for i, j in enumerate(jobs)
    )

    prompt = f"""以下是抓取到的校招岗位列表，请根据求职者的技能背景，对每个岗位给出：
1. 匹配度（高/中/低）
2. 一句话理由

求职者背景：
{PROFILE}

岗位列表：
{job_text}

请用JSON数组格式输出，每个元素包含 index(序号), match(高/中/低), reason(一句话理由)。
只输出JSON，不要其他内容。"""

    result = _call_llm(prompt, system="你是一个校招分析助手，帮助求职者评估岗位匹配度。")

    if not result:
        return jobs

    try:
        # Extract JSON from response
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        analyses = json.loads(result)

        for item in analyses:
            idx = item.get("index", 0) - 1
            if 0 <= idx < len(jobs):
                jobs[idx]["llm_match"] = item.get("match", "")
                jobs[idx]["llm_reason"] = item.get("reason", "")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[WARN] LLM 返回解析失败: {e}")

    return jobs


def generate_smart_report(jobs: list, new_jobs: list) -> str:
    """用 LLM 生成自然语言的每日播报"""
    cfg = config_loader.get_llm_config()
    if not cfg["api_key"]:
        return ""

    today = datetime.now().strftime("%Y-%m-%d")

    # Build context
    from collections import Counter
    by_company = Counter(j.get("company", "") for j in jobs)
    new_by_company = Counter(j.get("company", "") for j in new_jobs)

    context = f"""今天是 {today}，秋招信息抓取结果如下：

总共抓取到 {len(jobs)} 条岗位信息，涉及 {len(by_company)} 家公司。
新增 {len(new_jobs)} 条（来自：{dict(new_by_company)}）。

新增岗位详情：
"""
    for j in new_jobs:
        match_info = f" [匹配度:{j.get('llm_match','')}]" if j.get('llm_match') else ""
        context += f"- [{j.get('company','')}] {j.get('title','')}{match_info}\n"
        if j.get("llm_reason"):
            context += f"  理由：{j['llm_reason']}\n"

    prompt = f"""{context}

求职者背景：
{PROFILE}

请生成一份简洁的每日秋招播报（中文，Markdown格式），包含：
1. 今日概要（1-2句话总结）
2. 重点关注（哪些岗位值得优先投递，为什么）
3. 行动建议（今天应该做什么）

风格要求：简洁实用，不要废话，像一个了解你的学长给你发的消息。"""

    result = _call_llm(prompt, system="你是一个秋招导师，帮助LLM方向的硕士生做求职决策。")
    return result


def check_llm_available() -> bool:
    """检查 LLM 是否可用"""
    cfg = config_loader.get_llm_config()
    if not cfg["api_key"]:
        return False
    test = _call_llm("回复OK", system="只回复OK两个字")
    return bool(test)


if __name__ == "__main__":
    if "--test" in sys.argv:
        print("[INFO] 测试 LLM 连接...")
        if check_llm_available():
            print("[OK] LLM API 可用")
        else:
            cfg = config_loader.get_llm_config()
            if not cfg["api_key"]:
                print("[FAIL] 未配置 LLM_API_KEY，请在 .env 中设置")
            else:
                print(f"[FAIL] 无法连接 {cfg['base_url']}")
    else:
        print("用法: python3 llm_analyzer.py --test")
