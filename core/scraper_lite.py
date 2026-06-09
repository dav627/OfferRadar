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
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/json",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

from core.config import get_profile


def _keywords():
    p = get_profile()
    return p["keywords"], p["exclude_keywords"]


KEYWORDS, EXCLUDE_KEYWORDS = _keywords()


def fetch_url(url: str, timeout: int = 15) -> str:
    import ssl
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [WARN] 抓取失败 {url[:40]}: {e}")
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


def scrape_tencent() -> list:
    """腾讯 - 官方 API（校招 type=2）"""
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    jobs = []
    for kw in KEYWORDS[:3]:
        kw_enc = urllib.parse.quote(kw)
        url = f"https://careers.tencent.com/tencentcareer/api/post/Query?keyword={kw_enc}&pageIndex=0&pageSize=20&language=zh-cn&area=cn&type=2"
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": HEADERS["User-Agent"],
                "Accept": "application/json",
                "Referer": "https://careers.tencent.com/",
            })
            raw = urllib.request.urlopen(req, timeout=10, context=ctx).read()
            data = json.loads(raw)
            posts = data.get("Data", {}).get("Posts") or []
            for p in posts:
                title = p.get("RecruitPostName", "")
                if not title:
                    continue
                if any(ex in title for ex in EXCLUDE_KEYWORDS):
                    continue
                post_id = p.get("PostId", "")
                jobs.append({
                    "company": "腾讯",
                    "title": title,
                    "department": p.get("BGName", ""),
                    "location": p.get("LocationName", ""),
                    "url": f"https://careers.tencent.com/jobdesc.html?postId={post_id}" if post_id else "",
                    "source": "tencent_api",
                    "scraped_at": datetime.now().isoformat(),
                })
        except Exception as e:
            print(f"  [WARN] 腾讯API({kw}): {e}")
    # 去重
    seen = set()
    unique = []
    for j in jobs:
        if j["title"] not in seen:
            seen.add(j["title"])
            unique.append(j)
    return unique


def scrape_generic(company: dict) -> list:
    """通用抓取 - 尝试已知招聘页面模式"""
    name = company["name"]

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
    global KEYWORDS, EXCLUDE_KEYWORDS
    KEYWORDS, EXCLUDE_KEYWORDS = _keywords()

    print(f"[INFO] 轻量级抓取开始 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    with open(COMPANY_LIST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    companies = data["companies"]

    all_jobs = []

    # Company-specific scrapers (有专用API或解析方式的公司)
    print("[INFO] 抓取字节跳动...")
    all_jobs.extend(scrape_bytedance())

    print("[INFO] 抓取腾讯...")
    all_jobs.extend(scrape_tencent())

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

    # Nowcoder aggregation
    print("[INFO] 牛客网聚合搜索...")
    try:
        from core.sources import scrape_nowcoder
        nowcoder_jobs = scrape_nowcoder()
        if nowcoder_jobs:
            print(f"  [OK] 牛客: {len(nowcoder_jobs)} 条")
            all_jobs.extend(nowcoder_jobs)
    except Exception as e:
        print(f"  [WARN] 牛客: {e}")

    # Cookie-based scraping (for companies with saved cookies)
    try:
        from core.sources import get_cookie_status, scrape_with_cookies
        cookies = get_cookie_status()
        for key, info in cookies.items():
            if info.get("saved"):
                print(f"[INFO] Cookie抓取: {info['name']}...")
                try:
                    cookie_jobs = scrape_with_cookies(key)
                    if cookie_jobs:
                        print(f"  [OK] {info['name']}: {len(cookie_jobs)} 条")
                        all_jobs.extend(cookie_jobs)
                except Exception as e:
                    print(f"  [WARN] {info['name']}: {e}")
    except Exception:
        pass

    # Save to DB (dedup) + JSON
    from core.db import upsert_jobs
    result = upsert_jobs(all_jobs)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "scraped_at": datetime.now().isoformat(),
        "scraper": "lite",
        "total_jobs": len(all_jobs),
        "new_jobs": result["new"],
        "jobs": all_jobs
    }
    output_path = RESULTS_DIR / f"scrape_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    with open(RESULTS_DIR / "latest.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] 共抓取 {len(all_jobs)} 条，新增 {result['new']} 条（去重后）")
    print(f"[SAVED] {output_path}")
    return all_jobs


if __name__ == "__main__":
    run()
