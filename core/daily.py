#!/usr/bin/env python3
"""
每日一键执行：抓取 + 邮箱监控 + LLM分析 + 播报 + 推送
用法:
  python3 run_daily.py                # 完整执行
  python3 run_daily.py --lite         # 轻量模式（不需要Playwright）
  python3 run_daily.py --no-email     # 跳过邮箱检查
  python3 run_daily.py --no-push      # 跳过微信/QQ推送
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from core import PROJECT_ROOT


USE_LITE = "--lite" in sys.argv
SKIP_EMAIL = "--no-email" in sys.argv or "--no-gmail" in sys.argv
SKIP_PUSH = "--no-push" in sys.argv


async def main():
    print("=" * 60)
    print(f"  秋招Agent - 每日更新")
    print(f"  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  模式: {'轻量' if USE_LITE else '完整'} | 邮箱: {'跳过' if SKIP_EMAIL else '启用'}")
    print("=" * 60)

    total_steps = 2 + (0 if SKIP_EMAIL else 1)
    step = 1

    # Step 1: 抓取
    print(f"\n[Step {step}/{total_steps}] 开始抓取各公司招聘信息...")
    print("-" * 40)
    if USE_LITE:
        from core.scraper_lite import run as lite_scrape
        results = lite_scrape()
        job_count = len(results)
    else:
        try:
            from core.scraper import RecruitmentScraper
            scraper = RecruitmentScraper()
            results = await scraper.run()
            job_count = len(results)
        except Exception as e:
            print(f"[WARN] Playwright抓取失败({e})，回退到轻量模式...")
            from core.scraper_lite import run as lite_scrape
            results = lite_scrape()
            job_count = len(results)
    step += 1

    # Step 2: 邮箱监控
    email_report = ""
    if not SKIP_EMAIL:
        from core import config as config_loader
        cfg = config_loader.get_email_config()
        method = cfg.get("method", "")
        has_imap = method == "imap" and cfg.get("address") and cfg.get("password")
        has_gmail = method == "gmail_api" or (not method and (PROJECT_ROOT / "token.json").exists())
        if has_imap or has_gmail:
            print(f"\n[Step {step}/{total_steps}] 检查招聘邮件...")
            print("-" * 40)
            try:
                from core.email_monitor import fetch_emails, generate_email_report, save_results
                emails = fetch_emails(cfg, days=1)
                if emails:
                    save_results(emails)
                    email_report = generate_email_report(emails)
            except Exception as e:
                print(f"[WARN] 邮箱监控失败: {e}")
        else:
            print(f"\n[Step {step}/{total_steps}] 邮箱未配置，跳过")
        step += 1

    # Step 3: 播报 + Excel
    print(f"\n[Step {step}/{total_steps}] 生成每日播报 + 更新Excel...")
    print("-" * 40)
    from core.report import run as generate_report
    generate_report()

    # Append email report
    if email_report:
        today = datetime.now().strftime("%Y-%m-%d")
        report_path = Path(__file__).parent / "每日播报" / f"{today}.md"
        if report_path.exists():
            with open(report_path, "a", encoding="utf-8") as f:
                f.write(email_report)
            print("[INFO] 邮件监控已追加到播报")

    # Push
    if not SKIP_PUSH:
        print(f"\n[Push] 推送每日播报...")
        print("-" * 40)
        try:
            from core.notifier import send_daily_report
            send_daily_report()
        except Exception as e:
            print(f"[WARN] 推送失败: {e}")
            print("  请在 config.yaml 的 push 段配置推送渠道")

    print("\n" + "=" * 60)
    print(f"  执行完毕！")
    print(f"  - 岗位: {job_count} 条")
    print(f"  - 邮箱: {'已检查' if not SKIP_EMAIL and email_report else '跳过'}")
    print(f"  - 推送: {'已发送' if not SKIP_PUSH else '跳过'}")
    print(f"  - 播报: 每日播报/{datetime.now().strftime('%Y-%m-%d')}.md")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
