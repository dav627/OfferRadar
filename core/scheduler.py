"""
增量爬虫调度引擎
- 不同梯队不同抓取频率（S=每次, A=每次, B=每2次, C=每3次）
- 失败自动重试（最多3次，指数退避）
- 限速：每个请求间隔 1-3 秒，防封
- 记录每个公司的最后抓取时间和成功/失败状态
"""

import json
import time
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from core import DATA_DIR
from core.db import _conn as _db_conn, upsert_jobs

# 梯队 → 每 N 次全量抓取时才抓这个梯队
TIER_FREQUENCY = {"S": 1, "A": 1, "B": 2, "C": 3}
MAX_RETRIES = 3


def _sched_conn():
    conn = _db_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS scrape_schedule (
        company TEXT PRIMARY KEY,
        tier TEXT DEFAULT 'B',
        last_scraped TEXT DEFAULT '',
        last_status TEXT DEFAULT '',
        fail_count INTEGER DEFAULT 0,
        total_scraped INTEGER DEFAULT 0,
        scraper_type TEXT DEFAULT 'generic'
    )""")
    conn.commit()
    return conn


def init_schedule(companies: list):
    """从公司清单初始化调度表"""
    conn = _sched_conn()
    for c in companies:
        try:
            conn.execute("INSERT OR IGNORE INTO scrape_schedule (company, tier) VALUES (?,?)",
                         (c["name"], c.get("tier", "B")))
        except Exception:
            pass
    conn.commit()
    conn.close()


def should_scrape(company: str, tier: str, run_count: int) -> bool:
    """判断本轮是否应该抓取该公司"""
    freq = TIER_FREQUENCY.get(tier, 2)
    return run_count % freq == 0


def record_result(company: str, success: bool, job_count: int = 0):
    """记录抓取结果"""
    conn = _sched_conn()
    now = datetime.now().isoformat()
    if success:
        conn.execute(
            "UPDATE scrape_schedule SET last_scraped=?, last_status='success', fail_count=0, total_scraped=total_scraped+? WHERE company=?",
            (now, job_count, company))
    else:
        conn.execute(
            "UPDATE scrape_schedule SET last_scraped=?, last_status='failed', fail_count=fail_count+1 WHERE company=?",
            (now, company))
    conn.commit()
    conn.close()


def get_schedule_status() -> list:
    """获取所有公司的调度状态"""
    conn = _sched_conn()
    rows = conn.execute("SELECT * FROM scrape_schedule ORDER BY tier, company").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def run_scheduled_scrape(run_count: int = 1) -> dict:
    """
    执行一轮智能调度抓取
    根据梯队频率决定抓取哪些公司，失败自动重试，限速防封
    """
    from core.config import get_profile
    from core import PROJECT_ROOT

    profile = get_profile()
    company_path = PROJECT_ROOT / "公司清单.json"
    if not company_path.exists():
        return {"total": 0, "new": 0, "errors": []}

    with open(company_path, encoding="utf-8") as f:
        companies = json.load(f).get("companies", [])

    init_schedule(companies)

    all_jobs = []
    errors = []
    scraped_count = 0

    # Phase 1: 专用 API 抓取（字节/百度/腾讯），这些每次都跑
    print("[调度] Phase 1: 专用API抓取")
    api_scrapers = _get_api_scrapers()
    for name, scraper_fn in api_scrapers.items():
        try:
            jobs = _retry_scrape(scraper_fn, name)
            all_jobs.extend(jobs)
            record_result(name, True, len(jobs))
            scraped_count += 1
            _rate_limit()
        except Exception as e:
            record_result(name, False)
            errors.append(f"{name}: {e}")

    # Phase 2: 通用抓取（按梯队频率调度）
    print(f"[调度] Phase 2: 通用抓取 (第{run_count}轮)")
    for c in companies:
        name = c["name"]
        tier = c.get("tier", "B")
        if name in api_scrapers:
            continue
        if not should_scrape(name, tier, run_count):
            continue

        try:
            from core.scraper_lite import scrape_generic
            jobs = _retry_scrape(lambda: scrape_generic(c), name)
            if jobs:
                all_jobs.extend(jobs)
                record_result(name, True, len(jobs))
            else:
                record_result(name, True, 0)
            scraped_count += 1
            _rate_limit()
        except Exception as e:
            record_result(name, False)
            errors.append(f"{name}: {e}")

    # Phase 3: 插件爬虫
    print("[调度] Phase 3: 插件爬虫")
    try:
        from scrapers import run_all_plugins
        plugin_jobs = run_all_plugins()
        all_jobs.extend(plugin_jobs)
    except Exception as e:
        errors.append(f"插件: {e}")

    # Phase 4: 牛客聚合
    print("[调度] Phase 4: 牛客聚合")
    try:
        from core.sources import scrape_nowcoder
        nowcoder = scrape_nowcoder()
        all_jobs.extend(nowcoder)
    except Exception as e:
        errors.append(f"牛客: {e}")

    # Phase 5: Cookie 公司
    try:
        from core.sources import get_cookie_status, scrape_with_cookies
        for key, info in get_cookie_status().items():
            if info.get("saved"):
                try:
                    jobs = scrape_with_cookies(key)
                    if jobs:
                        all_jobs.extend(jobs)
                        record_result(info["name"], True, len(jobs))
                except Exception as e:
                    errors.append(f"{info['name']}(cookie): {e}")
    except Exception:
        pass

    # 入库
    result = upsert_jobs(all_jobs)

    print(f"[调度] 完成: 抓取{scraped_count}家, 共{len(all_jobs)}条, 新增{result['new']}条, 错误{len(errors)}个")
    return {"total": len(all_jobs), "new": result["new"], "scraped": scraped_count, "errors": errors}


def _get_api_scrapers() -> dict:
    from core.scraper_lite import scrape_bytedance, scrape_tencent, scrape_huawei
    return {
        "字节跳动": scrape_bytedance,
        "腾讯": scrape_tencent,
        "华为": scrape_huawei,
    }


def _retry_scrape(scraper_fn, name: str, max_retries: int = MAX_RETRIES) -> list:
    """带重试的抓取"""
    for attempt in range(max_retries):
        try:
            result = scraper_fn()
            return result if result else []
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.random()
                print(f"  [RETRY] {name} 第{attempt+1}次失败, {wait:.1f}s后重试: {e}")
                time.sleep(wait)
            else:
                raise


def _rate_limit():
    """随机延迟 0.5-2 秒，防封"""
    time.sleep(random.uniform(0.5, 2.0))
