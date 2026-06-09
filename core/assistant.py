"""
多轮对话求职助手
支持工具调用：查询岗位库、分析简历匹配、对比岗位
"""

import json
from core.config import get_llm_config, get_profile
from core.llm import _call_llm
from core.db import get_all_jobs, get_stats, get_expiring_jobs
from core.resume_match import get_resume_text

SYSTEM_PROMPT = """你是 OfferRadar 求职助手，帮助用户做秋招求职决策。

你可以访问以下数据：
{context}

你的能力：
1. 回答求职策略问题（投递顺序、面试准备、薪资谈判等）
2. 对比不同公司/岗位的优劣
3. 基于用户简历分析岗位匹配度
4. 给出具体的行动建议

规则：
- 用中文回答，简洁实用
- 基于真实数据回答，不编造岗位信息
- 给出具体可执行的建议，不说废话
"""


def _build_context() -> str:
    """构建对话上下文（岗位数据摘要）"""
    stats = get_stats()
    profile = get_profile()
    resume = get_resume_text()

    # 各状态岗位摘要
    jobs_summary = []
    for status in ["待投递", "已投递", "面试中", "offer"]:
        jobs = get_all_jobs(status=status)
        if jobs:
            names = ", ".join(f"{j['company']}-{j['title'][:15]}" for j in jobs[:5])
            extra = f" 等{len(jobs)}个" if len(jobs) > 5 else ""
            jobs_summary.append(f"  {status}: {names}{extra}")

    expiring = get_expiring_jobs(3)
    exp_text = ""
    if expiring:
        exp_text = "\n即将截止: " + ", ".join(f"{j['company']}({j['deadline']})" for j in expiring[:3])

    context = f"""求职方向: {profile['target_role']} ({profile['graduation']}届)
岗位库: 共{stats['total']}个岗位
状态分布: {json.dumps(stats.get('by_status', {}), ensure_ascii=False)}
{chr(10).join(jobs_summary) if jobs_summary else '  暂无进行中的投递'}
{exp_text}
简历: {'已上传' if resume else '未上传'}
技能: {profile.get('bio', '未填写')[:100]}"""

    return context


class ChatSession:
    def __init__(self):
        self.history = []
        self.max_history = 10

    def chat(self, user_message: str) -> str:
        cfg = get_llm_config()
        if not cfg["api_key"]:
            return "请先在系统配置中填写 LLM API Key，才能使用对话助手。"

        context = _build_context()
        system = SYSTEM_PROMPT.format(context=context)

        # 检测是否需要查数据库
        response = ""
        if any(kw in user_message for kw in ["对比", "比较", "vs", "VS", "哪个好"]):
            response = self._handle_compare(user_message, system)
        elif any(kw in user_message for kw in ["匹配", "适合", "简历"]):
            response = self._handle_match(user_message, system)
        elif any(kw in user_message for kw in ["查", "搜索", "有哪些", "列出"]):
            response = self._handle_search(user_message, system)
        else:
            response = self._general_chat(user_message, system)

        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": response})
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]

        return response

    def _general_chat(self, msg: str, system: str) -> str:
        messages_text = "\n".join(
            f"{'用户' if m['role']=='user' else '助手'}: {m['content']}"
            for m in self.history[-6:]
        )
        prompt = f"对话历史:\n{messages_text}\n\n用户: {msg}" if messages_text else msg
        return _call_llm(prompt, system) or "抱歉，请检查 LLM API 配置。"

    def _handle_compare(self, msg: str, system: str) -> str:
        all_jobs = get_all_jobs()
        # 找出提到的公司
        mentioned = [j for j in all_jobs if j["company"] in msg or j["title"][:6] in msg][:10]
        job_info = "\n".join(f"- {j['company']} | {j['title']} | {j['location']} | 状态:{j['status']}" for j in mentioned)
        prompt = f"用户想对比岗位:\n{msg}\n\n相关岗位数据:\n{job_info or '未找到匹配岗位'}"
        return _call_llm(prompt, system) or "未找到相关岗位信息。"

    def _handle_match(self, msg: str, system: str) -> str:
        resume = get_resume_text()
        prompt = f"用户问: {msg}\n\n简历摘要: {resume[:500] if resume else '未上传简历'}"
        return _call_llm(prompt, system) or "请先上传简历。"

    def _handle_search(self, msg: str, system: str) -> str:
        all_jobs = get_all_jobs()
        keywords = msg.replace("查", "").replace("搜索", "").replace("有哪些", "").replace("列出", "").strip().split()
        matched = [j for j in all_jobs if any(kw in j["title"] or kw in j["company"] for kw in keywords)][:15]
        job_info = "\n".join(f"- {j['company']} | {j['title']} | {j['location']} | {j['status']}" for j in matched)
        prompt = f"用户查询: {msg}\n\n查到{len(matched)}条:\n{job_info or '无匹配结果'}"
        return _call_llm(prompt, system) or "未找到相关岗位。"


# Global session
_session = ChatSession()


def chat(message: str) -> str:
    return _session.chat(message)


def reset_session():
    global _session
    _session = ChatSession()
