"""
简历匹配分析
上传简历文本/PDF，LLM 对比 JD 给出匹配度和修改建议
"""

import json
from pathlib import Path
from core import PROJECT_ROOT, DATA_DIR
from core.config import get_llm_config, get_profile

RESUME_DIR = DATA_DIR / "resume"
RESUME_DIR.mkdir(parents=True, exist_ok=True)
RESUME_PATH = RESUME_DIR / "resume.txt"


def save_resume_text(text: str):
    RESUME_PATH.write_text(text, encoding="utf-8")


def get_resume_text() -> str:
    if RESUME_PATH.exists():
        return RESUME_PATH.read_text(encoding="utf-8")
    return ""


def match_job(job_title: str, job_company: str, job_url: str = "") -> dict:
    """用 LLM 分析简历与岗位的匹配度"""
    from core.llm import _call_llm

    resume = get_resume_text()
    if not resume:
        return {"error": "未上传简历，请在「简历匹配」页粘贴你的简历内容"}

    cfg = get_llm_config()
    if not cfg["api_key"]:
        return {"error": "未配置 LLM API，无法分析"}

    prompt = f"""请分析以下简历与目标岗位的匹配情况。

## 目标岗位
公司：{job_company}
岗位：{job_title}

## 简历内容
{resume[:3000]}

请输出以下内容（中文）：
1. **匹配度评分**：高/中/低
2. **命中技能**：简历中与该岗位匹配的技能点（列举3-5个）
3. **缺失技能**：岗位可能要求但简历中未体现的（列举2-3个）
4. **简历优化建议**：针对这个岗位，简历应该如何调整（2-3条具体建议）
5. **面试准备提示**：该岗位面试可能会问的技术方向（2-3个）"""

    result = _call_llm(prompt, system="你是一个资深HR和技术面试官，帮助候选人评估岗位匹配度。")
    if not result:
        return {"error": "LLM 调用失败"}

    return {"analysis": result, "job": f"{job_company} - {job_title}"}
