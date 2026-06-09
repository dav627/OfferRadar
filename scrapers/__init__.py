"""
插件化爬虫框架
每个公司一个 .py 文件，自动发现加载。

编写新爬虫：
1. 在 scrapers/ 下创建 xxx.py
2. 实现 scrape() 函数，返回 list[dict]
3. 每个 dict 至少包含 company, title 字段
4. 可选字段: department, location, url, source

示例 scrapers/example.py:

    COMPANY = "示例公司"

    def scrape() -> list:
        return [{"company": COMPANY, "title": "算法工程师", "url": "https://..."}]
"""

import importlib
import pkgutil
from pathlib import Path


def discover_scrapers() -> dict:
    """自动发现 scrapers/ 目录下的所有爬虫模块"""
    scrapers = {}
    pkg_path = Path(__file__).parent

    for importer, modname, ispkg in pkgutil.iter_modules([str(pkg_path)]):
        if modname.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"scrapers.{modname}")
            if hasattr(mod, "scrape") and callable(mod.scrape):
                company = getattr(mod, "COMPANY", modname)
                scrapers[modname] = {"module": mod, "company": company}
        except Exception as e:
            print(f"[WARN] 加载爬虫插件 {modname} 失败: {e}")

    return scrapers


def run_all_plugins() -> list:
    """执行所有插件爬虫，返回合并的岗位列表"""
    scrapers = discover_scrapers()
    all_jobs = []
    for name, info in scrapers.items():
        try:
            jobs = info["module"].scrape()
            if jobs:
                print(f"  [插件] {info['company']}: {len(jobs)} 条")
                all_jobs.extend(jobs)
        except Exception as e:
            print(f"  [插件ERR] {info['company']}: {e}")
    return all_jobs
