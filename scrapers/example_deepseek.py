"""
示例爬虫插件：DeepSeek 招聘页
展示如何编写自定义爬虫插件
"""

import json
import ssl
import urllib.request
from datetime import datetime

COMPANY = "DeepSeek"


def scrape() -> list:
    """抓取 DeepSeek 招聘页面"""
    url = "https://www.deepseek.com/careers"
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        html = urllib.request.urlopen(req, timeout=10, context=ctx).read().decode("utf-8", "ignore")

        # DeepSeek 的招聘页比较简单，尝试提取岗位
        import re
        jobs = []
        # 常见模式：包含"工程师"或"研究员"的文本
        matches = re.findall(r'>([^<]{5,50}(?:工程师|研究员|Engineer|Researcher)[^<]{0,20})<', html)
        for m in matches:
            m = m.strip()
            if len(m) > 5:
                jobs.append({
                    "company": COMPANY,
                    "title": m,
                    "url": url,
                    "source": "plugin_deepseek",
                    "scraped_at": datetime.now().isoformat(),
                })
        return jobs
    except Exception:
        return []
