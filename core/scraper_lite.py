#!/usr/bin/env python3
"""
轻量级抓取方案 - 不依赖Playwright
使用 urllib + 正则 抓取可以直接获取的招聘信息
适用于Playwright不可用时的备选方案
"""

import json
import re
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from core import PROJECT_ROOT, DATA_DIR
COMPANY_LIST_PATH = PROJECT_ROOT / "公司清单.json"
RESULTS_DIR = DATA_DIR / "抓取结果"
RESULTS_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/json",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import get_profile as _get_profile
_profile = _get_profile()
KEYWORDS = _profile["keywords"]
EXCLUDE_KEYWORDS = _profile["exclude_keywords"]


def fetch_url(url: str, timeout: int = 15) -> str:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return ""


def extract_jobs_from_html(html: str, company: str, url: str) -> list:
    """Extract job titles from HTML using regex patterns"""
    jobs = []
    seen = set()

    patterns = [
        # Common patterns for job titles in recruitment sites
        r'"(?:title|name|positionName|job_name)"[:\s]*"([^"]{4,60})"',
        r'class="[^"]*(?:title|name|position)[^"]*"[^>]*>([^<]{4,60})<',
        r'>([^<]{3,50}(?:大模型|LLM|NLP|算法工程师|研究员|AI)[^<]{0,30})<',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html)
        for m in matches:
            m = m.strip()
            if m in seen or len(m) < 4 or len(m) > 60:
                continue
            if any(kw in m for kw in KEYWORDS) and not any(ex in m for ex in EXCLUDE_KEYWORDS):
                seen.add(m)
                jobs.append({
                    "company": company,
                    "title": m,
                    "url": url,
                    "source": "lite_scraper",
                    "scraped_at": datetime.now().isoformat()
                })

    return jobs


def scrape_bytedance() -> list:
    """字节跳动 - 解析内嵌JSON数据"""
    url = "https://jobs.bytedance.com/campus"
    html = fetch_url(url)
    jobs = []

    # Extract embedded config
    match = re.search(r'id="js-websiteInfo"[^>]*>(.*?)</script>', html)
    if match:
        try:
            data = json.loads(match.group(1))
            tenant = data.get("tenant_info", {})
            jdy_str = tenant.get("jindouyunConfig", "")
            if jdy_str:
                jdy = json.loads(jdy_str)
                domains = jdy.get("pageConfig", {}).get("domainModuleConfig", {}).get("domainList", [])
                for domain in domains:
                    domain_name = domain.get("domain", "")
                    for direction in domain.get("direction", []):
                        title = direction.get("title", "")
                        if title and any(kw in title for kw in KEYWORDS):
                            jobs.append({
                                "company": "字节跳动",
                                "title": f"[{domain_name}] {title}",
                                "department": domain_name,
                                "url": url,
                                "source": "bytedance_embedded",
                                "scraped_at": datetime.now().isoformat()
                            })
        except (json.JSONDecodeError, KeyError):
            pass

    # Also try extracting from filter desc
    if match:
        try:
            data = json.loads(match.group(1))
            filter_desc = json.loads(data.get("tenant_info", {}).get("filter_extra_desc", "{}"))
            for k, v in filter_desc.items():
                if "2027" in v.get("desc", "") or "2026" in v.get("desc", ""):
                    jobs.append({
                        "company": "字节跳动",
                        "title": f"[招聘信息] {v.get('title', '')}: {v.get('desc', '')}",
                        "url": url,
                        "source": "bytedance_meta",
                        "scraped_at": datetime.now().isoformat()
                    })
        except Exception:
            pass

    return jobs


def scrape_huawei() -> list:
    """华为 - 校招页面"""
    url = "https://career.huawei.com/reccampportal/portal5/campus-recruitment.html"
    html = fetch_url(url)
    return extract_jobs_from_html(html, "华为", url)


def scrape_generic(company: dict) -> list:
    """通用抓取 - 尝试已知招聘页面模式"""
    name = company["name"]
    urls_to_try = []

    # Common URL patterns for Chinese tech companies
    url_patterns = {
        "美团": ["https://campus.meituan.com"],
        "快手": ["https://zhaopin.kuaishou.cn"],
        "百度": ["https://talent.baidu.com/jobs/list"],
        "京东": ["https://campus.jd.com"],
        "网易": ["https://campus.163.com"],
        "小红书": ["https://job.xiaohongshu.com"],
        "B站": ["https://campus.bilibili.com"],
        "科大讯飞": ["https://campus.iflytek.com"],
    }

    urls = url_patterns.get(name, [])
    all_jobs = []
    for url in urls:
        html = fetch_url(url)
        if html:
            jobs = extract_jobs_from_html(html, name, url)
            all_jobs.extend(jobs)

    return all_jobs


def run():
    print(f"[INFO] 轻量级抓取开始 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    with open(COMPANY_LIST_PATH, "r") as f:
        data = json.load(f)
    companies = data["companies"]

    all_jobs = []

    # Company-specific scrapers
    print("[INFO] 抓取字节跳动...")
    all_jobs.extend(scrape_bytedance())

    print("[INFO] 抓取华为...")
    all_jobs.extend(scrape_huawei())

    # Generic scraper with thread pool
    print("[INFO] 并发抓取其他公司...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(scrape_generic, c): c for c in companies}
        for future in as_completed(futures):
            company = futures[future]
            try:
                jobs = future.result()
                if jobs:
                    print(f"  [OK] {company['name']}: {len(jobs)} 条")
                    all_jobs.extend(jobs)
            except Exception as e:
                print(f"  [ERR] {company['name']}: {e}")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "scraped_at": datetime.now().isoformat(),
        "scraper": "lite",
        "total_jobs": len(all_jobs),
        "jobs": all_jobs
    }

    output_path = RESULTS_DIR / f"scrape_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    latest_path = RESULTS_DIR / "latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] 共抓取 {len(all_jobs)} 条岗位信息")
    print(f"[SAVED] {output_path}")
    return all_jobs


if __name__ == "__main__":
    run()
