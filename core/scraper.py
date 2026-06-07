#!/usr/bin/env python3
"""
秋招信息自动抓取脚本
使用 Playwright headless browser 抓取各公司校园招聘页面
"""

import json
import os
import re
import asyncio
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout

from core import PROJECT_ROOT, DATA_DIR
COMPANY_LIST_PATH = PROJECT_ROOT / "公司清单.json"
RESULTS_DIR = DATA_DIR / "抓取结果"
RESULTS_DIR.mkdir(exist_ok=True)

KEYWORDS = ["大模型", "LLM", "NLP", "RLHF", "RAG", "Agent", "对齐", "强化学习",
            "自然语言处理", "对话", "微调", "算法", "大模型应用"]

EXCLUDE_KEYWORDS = ["多模态", "基座模型", "预训练", "foundation", "视觉",
                    "图像", "语音", "CV", "计算机视觉", "multimodal"]


@dataclass
class JobInfo:
    company: str
    title: str
    location: str = ""
    department: str = ""
    requirements: str = ""
    url: str = ""
    salary: str = ""
    deadline: str = ""
    source: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())


class RecruitmentScraper:
    def __init__(self):
        with open(COMPANY_LIST_PATH, "r") as f:
            data = json.load(f)
        self.companies = data["companies"]
        self.keywords = data["meta"]["keywords"]
        self.results: list[JobInfo] = []

    async def run(self):
        async with async_playwright() as p:
            # Prefer system Chrome to avoid downloading Playwright's Chromium
            try:
                browser = await p.chromium.launch(channel="chrome", headless=True)
            except Exception:
                browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN"
            )

            for company in self.companies:
                try:
                    await self._scrape_company(context, company)
                except Exception as e:
                    print(f"[ERROR] {company['name']}: {e}")

            await browser.close()

        self._save_results()
        return self.results

    async def _scrape_company(self, context, company: dict):
        name = company["name"]
        print(f"[INFO] 正在抓取: {name}")

        scrapers = {
            "字节跳动": self._scrape_bytedance,
            "腾讯": self._scrape_tencent,
            "阿里巴巴": self._scrape_alibaba,
            "百度": self._scrape_baidu,
            "美团": self._scrape_meituan,
            "华为": self._scrape_huawei,
            "快手": self._scrape_kuaishou,
            "小红书": self._scrape_xiaohongshu,
        }

        if name in scrapers:
            page = await context.new_page()
            try:
                await scrapers[name](page, company)
            except PlaywrightTimeout:
                print(f"[TIMEOUT] {name}: 页面加载超时")
            except Exception as e:
                print(f"[ERROR] {name}: {e}")
            finally:
                await page.close()
        else:
            # Generic scraper for other companies
            page = await context.new_page()
            try:
                await self._scrape_generic(page, company)
            except Exception as e:
                print(f"[SKIP] {name}: {e}")
            finally:
                await page.close()

    async def _scrape_bytedance(self, page: Page, company: dict):
        url = "https://jobs.bytedance.com/campus/position?keywords=大模型&category=&location=&project=7194661126919358757&type=2"
        await page.goto(url, timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Try to find job cards
        job_cards = await page.query_selector_all('[class*="position-card"], [class*="job-card"], [class*="item"]')

        if not job_cards:
            # Fallback: extract text content
            content = await page.content()
            self._extract_from_html(content, company["name"], url)
            return

        for card in job_cards[:20]:
            try:
                title_el = await card.query_selector('[class*="title"], [class*="name"], h3, h4')
                title = await title_el.inner_text() if title_el else ""

                location_el = await card.query_selector('[class*="city"], [class*="location"]')
                location = await location_el.inner_text() if location_el else ""

                if title and any(kw in title for kw in KEYWORDS):
                    self.results.append(JobInfo(
                        company=company["name"],
                        title=title.strip(),
                        location=location.strip(),
                        url=url,
                        source="bytedance_campus"
                    ))
            except Exception:
                continue

        # Also search for LLM/算法 keywords
        for keyword in ["LLM", "算法", "NLP"]:
            url2 = f"https://jobs.bytedance.com/campus/position?keywords={keyword}&project=7194661126919358757&type=2"
            await page.goto(url2, timeout=20000, wait_until="networkidle")
            await page.wait_for_timeout(2000)
            cards = await page.query_selector_all('[class*="position-card"], [class*="job-card"], [class*="item"]')
            for card in cards[:10]:
                try:
                    title_el = await card.query_selector('[class*="title"], [class*="name"], h3, h4')
                    title = await title_el.inner_text() if title_el else ""
                    if title and title not in [r.title for r in self.results]:
                        self.results.append(JobInfo(
                            company=company["name"],
                            title=title.strip(),
                            url=url2,
                            source="bytedance_campus"
                        ))
                except Exception:
                    continue

    async def _scrape_tencent(self, page: Page, company: dict):
        url = "https://join.qq.com/post.html?query=大模型&tid=2"
        await page.goto(url, timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        cards = await page.query_selector_all('[class*="recruit-list"] li, [class*="position-item"], .recruit-item')
        for card in cards[:20]:
            try:
                title_el = await card.query_selector('[class*="title"], [class*="name"], h4, a')
                title = await title_el.inner_text() if title_el else ""

                location_el = await card.query_selector('[class*="city"], [class*="address"]')
                location = await location_el.inner_text() if location_el else ""

                if title:
                    self.results.append(JobInfo(
                        company=company["name"],
                        title=title.strip(),
                        location=location.strip(),
                        url="https://join.qq.com",
                        source="tencent_campus"
                    ))
            except Exception:
                continue

    async def _scrape_alibaba(self, page: Page, company: dict):
        url = "https://talent.alibaba.com/campus/position-list?campusType=freshman&query=大模型"
        await page.goto(url, timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        cards = await page.query_selector_all('[class*="position-item"], [class*="job-card"], .campus-item')
        for card in cards[:20]:
            try:
                title_el = await card.query_selector('[class*="title"], [class*="name"], h3')
                title = await title_el.inner_text() if title_el else ""

                dept_el = await card.query_selector('[class*="department"], [class*="bu-name"]')
                dept = await dept_el.inner_text() if dept_el else ""

                if title:
                    self.results.append(JobInfo(
                        company=company["name"],
                        title=title.strip(),
                        department=dept.strip(),
                        url="https://talent.alibaba.com/campus",
                        source="alibaba_campus"
                    ))
            except Exception:
                continue

    async def _scrape_baidu(self, page: Page, company: dict):
        url = "https://talent.baidu.com/jobs/list?keyword=大模型&recruitType=CAMPUS"
        await page.goto(url, timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        cards = await page.query_selector_all('[class*="job-item"], [class*="position-card"]')
        for card in cards[:20]:
            try:
                title_el = await card.query_selector('[class*="title"], [class*="name"]')
                title = await title_el.inner_text() if title_el else ""
                if title:
                    self.results.append(JobInfo(
                        company=company["name"],
                        title=title.strip(),
                        url=url,
                        source="baidu_campus"
                    ))
            except Exception:
                continue

    async def _scrape_meituan(self, page: Page, company: dict):
        url = "https://campus.meituan.com/recruit/search?keyword=大模型"
        await page.goto(url, timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        cards = await page.query_selector_all('[class*="job-item"], [class*="position-card"], [class*="recruit-card"]')
        for card in cards[:20]:
            try:
                title_el = await card.query_selector('[class*="title"], [class*="name"]')
                title = await title_el.inner_text() if title_el else ""
                if title:
                    self.results.append(JobInfo(
                        company=company["name"],
                        title=title.strip(),
                        url=url,
                        source="meituan_campus"
                    ))
            except Exception:
                continue

    async def _scrape_huawei(self, page: Page, company: dict):
        url = "https://career.huawei.com/reccampportal/portal5/campus-recruitment.html?keyword=大模型"
        await page.goto(url, timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        cards = await page.query_selector_all('[class*="job-item"], [class*="position"]')
        for card in cards[:20]:
            try:
                title_el = await card.query_selector('[class*="title"], [class*="name"]')
                title = await title_el.inner_text() if title_el else ""
                if title:
                    self.results.append(JobInfo(
                        company=company["name"],
                        title=title.strip(),
                        url=url,
                        source="huawei_campus"
                    ))
            except Exception:
                continue

    async def _scrape_kuaishou(self, page: Page, company: dict):
        url = "https://zhaopin.kuaishou.cn/recruit/campus/e/#/campus/job-list?keyword=大模型"
        await page.goto(url, timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        cards = await page.query_selector_all('[class*="job-item"], [class*="position"]')
        for card in cards[:20]:
            try:
                title_el = await card.query_selector('[class*="title"], [class*="name"]')
                title = await title_el.inner_text() if title_el else ""
                if title:
                    self.results.append(JobInfo(
                        company=company["name"],
                        title=title.strip(),
                        url=url,
                        source="kuaishou_campus"
                    ))
            except Exception:
                continue

    async def _scrape_xiaohongshu(self, page: Page, company: dict):
        url = "https://job.xiaohongshu.com/campus"
        await page.goto(url, timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        cards = await page.query_selector_all('[class*="job-item"], [class*="position"]')
        for card in cards[:20]:
            try:
                title_el = await card.query_selector('[class*="title"], [class*="name"]')
                title = await title_el.inner_text() if title_el else ""
                if title:
                    self.results.append(JobInfo(
                        company=company["name"],
                        title=title.strip(),
                        url=url,
                        source="xiaohongshu_campus"
                    ))
            except Exception:
                continue

    async def _scrape_generic(self, page: Page, company: dict):
        """Generic scraper - search Nowcoder for this company's positions"""
        name = company["name"]

        url = f"https://www.nowcoder.com/search?type=job&query={name}+大模型+校招"
        try:
            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            # Try to find job listing elements on Nowcoder
            selectors = [
                '.search-result-item a',
                '[class*="job-item"] a',
                '.result-item a',
                'a[href*="discuss"]',
            ]
            for sel in selectors:
                links = await page.query_selector_all(sel)
                for link in links[:15]:
                    try:
                        text = await link.inner_text()
                        text = text.strip()
                        if self._is_valid_job_title(text, name):
                            self.results.append(JobInfo(
                                company=name,
                                title=text,
                                url=url,
                                source="nowcoder_search"
                            ))
                    except Exception:
                        continue
                if self.results and any(r.company == name for r in self.results):
                    break

            # Fallback: extract from page text with stricter filtering
            if not any(r.company == name for r in self.results):
                content = await page.content()
                self._extract_from_html(content, name, url)

        except Exception:
            pass

    @staticmethod
    def _is_valid_job_title(text: str, company: str) -> bool:
        """Filter out noise, keep only real job titles"""
        if not text or len(text) < 6 or len(text) > 80:
            return False
        noise = ["搜索结果", "牛客网", "请仔细甄别", "AI生成", "如何成为",
                 "content", "title", "meta", "#", "http", "javascript",
                 "关注", "收藏", "分享", "登录", "注册", "首页"]
        if any(n in text for n in noise):
            return False
        job_markers = ["工程师", "算法", "研究员", "实习", "校招", "秋招",
                       "大模型", "LLM", "NLP", "Agent", "offer", "招聘"]
        if not any(m in text for m in job_markers):
            return False
        if any(ex in text for ex in EXCLUDE_KEYWORDS):
            return False
        return True

    def _extract_from_html(self, html: str, company: str, url: str):
        """Extract job titles from raw HTML with strict filtering"""
        patterns = [
            r'>([^<]{8,60}(?:大模型|LLM)(?:算法|应用)?(?:工程师|研究员)[^<]{0,15})<',
            r'>([^<]{6,60}(?:校招|秋招|2027)[^<]{0,30}(?:算法|工程师|研究员)[^<]{0,10})<',
        ]
        seen = set()
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for m in matches:
                m = m.strip()
                if m not in seen and self._is_valid_job_title(m, company):
                    seen.add(m)
                    self.results.append(JobInfo(
                        company=company,
                        title=m,
                        url=url,
                        source="html_extract"
                    ))

    def _merge_lite_results(self):
        """Merge in results from lite scraper (better for sites with server-rendered HTML)"""
        try:
            from core.scraper_lite import run as lite_run
            print("[INFO] 合并轻量抓取结果...")
            lite_jobs = lite_run()

            existing = {(r.company, r.title) for r in self.results}
            added = 0
            for job in lite_jobs:
                key = (job["company"], job["title"])
                if key not in existing:
                    fields = {k: v for k, v in job.items() if k in JobInfo.__dataclass_fields__}
                    self.results.append(JobInfo(**fields))
                    existing.add(key)
                    added += 1
            print(f"[INFO] 从lite合并了 {added} 条新岗位")
        except Exception as e:
            print(f"[WARN] 合并lite结果失败: {e}")

    def _save_results(self):
        self._merge_lite_results()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = RESULTS_DIR / f"scrape_{timestamp}.json"

        results_data = {
            "scraped_at": datetime.now().isoformat(),
            "total_jobs": len(self.results),
            "jobs": [asdict(j) for j in self.results]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)

        print(f"\n[DONE] 共抓取 {len(self.results)} 条岗位信息")
        print(f"[SAVED] {output_path}")

        # Also save latest results as a symlink-like file
        latest_path = RESULTS_DIR / "latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)


async def main():
    scraper = RecruitmentScraper()
    results = await scraper.run()
    return results


if __name__ == "__main__":
    asyncio.run(main())
