"""
数据源管理
方案1: 登录后抓取（Playwright + Cookie）
方案2: 第三方聚合源（牛客网搜索）
"""

import json
import ssl
import urllib.request
import urllib.parse
import re
from datetime import datetime
from pathlib import Path

from core import PROJECT_ROOT, DATA_DIR
from core.config import get_profile

COOKIE_DIR = DATA_DIR / "cookies"
COOKIE_DIR.mkdir(parents=True, exist_ok=True)

# 支持登录抓取的公司
LOGIN_PLATFORMS = {
    "alibaba":     {"name": "阿里巴巴", "login_url": "https://talent.alibaba.com/personal/login",  "search_url": "https://talent.alibaba.com/campus/position-list?campusType=freshman"},
    "meituan":     {"name": "美团",     "login_url": "https://campus.meituan.com",                "search_url": "https://campus.meituan.com/recruit/campus"},
    "kuaishou":    {"name": "快手",     "login_url": "https://zhaopin.kuaishou.cn/recruit/campus/e/#/official/campus/", "search_url": "https://zhaopin.kuaishou.cn/recruit/campus/e/#/official/campus/job-list"},
    "xiaohongshu": {"name": "小红书",   "login_url": "https://job.xiaohongshu.com",                "search_url": "https://job.xiaohongshu.com/campus"},
    "jd":          {"name": "京东",     "login_url": "https://campus.jd.com",                     "search_url": "https://campus.jd.com/#/job-list"},
    "bilibili":    {"name": "B站",     "login_url": "https://campus.bilibili.com",                "search_url": "https://campus.bilibili.com/campus/position/list"},
    "pinduoduo":   {"name": "拼多多",   "login_url": "https://careers.pinduoduo.com/campus",       "search_url": "https://careers.pinduoduo.com/campus/jobs"},
    "netease":     {"name": "网易",     "login_url": "https://campus.163.com",                    "search_url": "https://campus.163.com/app/index"},
}


def get_cookie_status() -> dict:
    """返回各公司 Cookie 状态"""
    status = {}
    for key, info in LOGIN_PLATFORMS.items():
        cookie_file = COOKIE_DIR / f"{key}.json"
        if cookie_file.exists():
            mtime = datetime.fromtimestamp(cookie_file.stat().st_mtime)
            status[key] = {"name": info["name"], "saved": True, "time": mtime.strftime("%m-%d %H:%M")}
        else:
            status[key] = {"name": info["name"], "saved": False, "time": ""}
    return status


def login_and_save(platform_key: str) -> bool:
    """打开浏览器让用户登录，保存 Cookie（需要 Playwright）"""
    if platform_key not in LOGIN_PLATFORMS:
        print(f"[ERROR] 未知平台: {platform_key}")
        return False

    info = LOGIN_PLATFORMS[platform_key]
    print(f"[INFO] 正在打开 {info['name']} 登录页面...")
    print("[INFO] 请在浏览器中完成登录，登录成功后关闭浏览器窗口即可")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] 需要安装 Playwright: pip install playwright && python -m playwright install chromium")
        return False

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=False)
        except Exception:
            browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(info["login_url"])

        # Wait for browser to close (user closes after login)
        try:
            page.wait_for_event("close", timeout=300000)
        except Exception:
            pass

        cookies = context.cookies()
        cookie_file = COOKIE_DIR / f"{platform_key}.json"
        with open(cookie_file, "w") as f:
            json.dump(cookies, f, indent=2)

        browser.close()

    print(f"[OK] {info['name']} Cookie 已保存")
    return True


def scrape_with_cookies(platform_key: str) -> list:
    """使用保存的 Cookie 登录后抓取岗位"""
    cookie_file = COOKIE_DIR / f"{platform_key}.json"
    if not cookie_file.exists():
        return []

    info = LOGIN_PLATFORMS.get(platform_key, {})
    if not info:
        return []

    profile = get_profile()
    keywords = profile["keywords"]
    exclude = profile["exclude_keywords"]

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    jobs = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        with open(cookie_file) as f:
            cookies = json.load(f)
        context.add_cookies(cookies)

        page = context.new_page()
        try:
            page.goto(info["search_url"], timeout=20000, wait_until="networkidle")
            page.wait_for_timeout(3000)

            # Generic: extract all text content and find job-like items
            content = page.content()
            # Look for job titles in the rendered page
            elements = page.query_selector_all('a, [class*="title"], [class*="name"], [class*="position"]')
            for el in elements[:100]:
                try:
                    text = el.inner_text().strip()
                    if len(text) < 5 or len(text) > 80:
                        continue
                    if any(kw in text for kw in keywords) and not any(ex in text for ex in exclude):
                        href = el.get_attribute("href") or ""
                        if href and not href.startswith("http"):
                            href = info["search_url"].split("//")[0] + "//" + info["search_url"].split("//")[1].split("/")[0] + href
                        jobs.append({
                            "company": info["name"],
                            "title": text,
                            "url": href,
                            "source": f"{platform_key}_cookie",
                            "scraped_at": datetime.now().isoformat(),
                        })
                except Exception:
                    continue
        except Exception as e:
            print(f"  [WARN] {info['name']} 抓取失败: {e}")
        finally:
            browser.close()

    # Dedup
    seen = set()
    unique = []
    for j in jobs:
        if j["title"] not in seen:
            seen.add(j["title"])
            unique.append(j)
    return unique


# ==================== 第三方聚合源 ====================

def scrape_nowcoder(keyword: str = "") -> list:
    """从牛客网搜索校招岗位信息"""
    profile = get_profile()
    keywords = profile["keywords"]
    exclude = profile["exclude_keywords"]
    if not keyword:
        keyword = " ".join(keywords[:2]) + " 校招"

    _ctx = ssl.create_default_context()
    _ctx.check_hostname = False
    _ctx.verify_mode = ssl.CERT_NONE

    kw_enc = urllib.parse.quote(keyword)
    jobs = []

    for search_type in ["all"]:
        url = f"https://www.nowcoder.com/search?type={search_type}&query={kw_enc}&page=1"
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html",
            })
            html = urllib.request.urlopen(req, timeout=10, context=_ctx).read().decode("utf-8", "ignore")

            matches = re.findall(r'>([^<]{10,80}(?:秋招|校招|大模型|LLM|offer|面经|内推|2027|2026)[^<]{0,30})<', html)
            noise = ["搜索结果", "牛客网", "请仔细甄别", "AI生成", "关注", "收藏", "登录", "首页",
                      "AI面试", "笔试、校招", "搜索", "document", "function"]
            for m in matches:
                m = m.strip().replace("&amp;nbsp;", " ").replace("&nbsp;", " ")
                if len(m) < 8 or any(n in m for n in noise):
                    continue
                if any(ex in m for ex in exclude):
                    continue
                jobs.append({
                    "company": "牛客聚合",
                    "title": m,
                    "url": f"https://www.nowcoder.com/search?type=all&query={kw_enc}",
                    "source": "nowcoder",
                    "scraped_at": datetime.now().isoformat(),
                })
        except Exception as e:
            print(f"  [WARN] 牛客: {e}")

    # Dedup
    seen = set()
    unique = []
    for j in jobs:
        if j["title"] not in seen:
            seen.add(j["title"])
            unique.append(j)
    return unique
