#!/usr/bin/env python3
"""
秋招Agent 统一启动器

用法:
  python3 launcher.py run              执行一次完整流程
  python3 launcher.py run --lite       轻量模式（无需Playwright）
  python3 launcher.py run --no-email   跳过邮箱检查
  python3 launcher.py run --no-push    跳过推送

  python3 launcher.py init             首次初始化（生成Excel等）
  python3 launcher.py status           查看系统状态
  python3 launcher.py test-push        发送测试推送
  python3 launcher.py test-llm         测试 LLM 接口
  python3 launcher.py gmail-auth       Gmail OAuth 授权

  python3 launcher.py schedule         查看定时任务状态
  python3 launcher.py schedule --on    开启定时任务
  python3 launcher.py schedule --off   关闭定时任务
  python3 launcher.py schedule --time 08:30  设置执行时间
"""

import sys
import os
import json
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core import PROJECT_ROOT, DATA_DIR
from core import config as cfg


def cmd_run():
    from core.daily import main as daily_main
    asyncio.run(daily_main())


def cmd_init():
    print("=== 秋招Agent 初始化 ===\n")

    print("[1/3] 检查依赖...")
    for pkg in ["openpyxl", "yaml"]:
        try:
            __import__(pkg)
            print(f"  [OK] {pkg}")
        except ImportError:
            print(f"  [MISS] {pkg} — 运行: pip3 install {'pyyaml' if pkg=='yaml' else pkg}")

    print("\n[2/3] 检查配置...")
    if (PROJECT_ROOT / "config.yaml").exists():
        print("  [OK] config.yaml")
    else:
        import shutil
        shutil.copy(PROJECT_ROOT / "config.yaml.example", PROJECT_ROOT / "config.yaml")
        print("  [INFO] 已从模板创建 config.yaml，请编辑填写")

    print("\n[3/3] 生成投递跟踪表...")
    excel = DATA_DIR / "秋招投递跟踪表.xlsx"
    if excel.exists():
        print(f"  [SKIP] 已存在")
    else:
        _generate_excel()
        print(f"  [OK] 已生成")

    for d in ["抓取结果", "每日播报", "email_results", "cookies", "logs"]:
        (DATA_DIR / d).mkdir(parents=True, exist_ok=True)

    print("\n=== 初始化完成 ===")
    print("下一步: python3 launcher.py run --lite --no-email --no-push")


def _generate_excel():
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "投递跟踪表"

    hfont = Font(bold=True, size=11, color='FFFFFF')
    hfill = PatternFill(start_color='002060', end_color='002060', fill_type='solid')
    border = Border(left=Side(style='thin'), right=Side(style='thin'),
                    top=Side(style='thin'), bottom=Side(style='thin'))

    headers = ['公司', '梯队', '类别', '部门/团队', '岗位名称', '工作地点',
               'JD核心要求', '匹配度', '投递链接', '内推信息', '网申开放',
               '网申截止', '薪资范围', '投递状态', '笔试时间', '面试进度', '备注']
    widths = [12, 6, 14, 16, 22, 10, 30, 8, 35, 20, 12, 12, 12, 10, 12, 15, 25]

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font, cell.fill, cell.border = hfont, hfill, border
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    with open(PROJECT_ROOT / "公司清单.json") as f:
        companies = json.load(f)["companies"]

    for row, c in enumerate(companies, 2):
        ws.cell(row=row, column=1, value=c["name"]).border = border
        ws.cell(row=row, column=2, value=c.get("tier", "")).border = border
        ws.cell(row=row, column=3, value=c.get("category", "")).border = border
        ws.cell(row=row, column=14, value="待关注").border = border

    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(companies)+1}"
    wb.save(DATA_DIR / "秋招投递跟踪表.xlsx")


def cmd_status():
    print("=== 秋招Agent 系统状态 ===\n")

    env_ok = (PROJECT_ROOT / "config.yaml").exists()
    cred_ok = (PROJECT_ROOT / "credentials.json").exists()
    token_ok = (PROJECT_ROOT / "token.json").exists()
    excel_ok = (DATA_DIR / "秋招投递跟踪表.xlsx").exists()

    print(f"  config.yaml:       {'已配置' if env_ok else '未配置 (cp config.yaml.example config.yaml)'}")
    print(f"  Gmail credentials: {'已配置' if cred_ok else '未配置'}")
    print(f"  Gmail token:       {'已授权' if token_ok else '未授权'}")
    print(f"  投递跟踪表:        {'已生成' if excel_ok else '未生成 (运行 launcher.py init)'}")

    push = cfg.get_push_config()
    active = [k for k, v in push.items() if v.get("enabled")]
    print(f"  推送渠道:          {', '.join(active) if active else '未配置'}")

    llm = cfg.get_llm_config()
    if llm["api_key"]:
        print(f"  LLM 接口:          {llm['model']} @ {llm['base_url'][:40]}")
    else:
        print(f"  LLM 接口:          未配置 (config.yaml → llm.api_key)")

    proxy = cfg.get_proxy()
    print(f"  代理设置:          {proxy.get('http') or '未设置'}")

    sched = cfg.get_schedule_config()
    print(f"  定时任务:          {'已启用 ' + sched['time'] if sched['enabled'] else '未启用'}")

    latest = DATA_DIR / "抓取结果" / "latest.json"
    if latest.exists():
        with open(latest) as f:
            d = json.load(f)
        print(f"\n  最近抓取: {d.get('scraped_at', '')[:16]} | {d.get('total_jobs', 0)} 条")

    reports = sorted((DATA_DIR / "每日播报").glob("*.md")) if (DATA_DIR / "每日播报").exists() else []
    if reports:
        print(f"  最近播报: {reports[-1].stem}")

    with open(PROJECT_ROOT / "公司清单.json") as f:
        n = len(json.load(f)["companies"])
    profile = cfg.get_profile()
    print(f"\n  监控公司: {n} 家 | {profile['target_role']} | {profile['graduation']}届校招")


def cmd_test_push():
    from core.notifier import send_notification
    send_notification("秋招Agent测试",
                      "推送配置成功！\n" + datetime.now().strftime("%Y-%m-%d %H:%M"))


def cmd_test_llm():
    from core.llm import check_llm_available
    print("[INFO] 测试 LLM 连接...")
    if check_llm_available():
        print("[OK] LLM API 可用")
    else:
        llm = cfg.get_llm_config()
        print("[FAIL]", "未配置 api_key" if not llm["api_key"] else f"无法连接 {llm['base_url']}")


def cmd_gmail_auth():
    if not (PROJECT_ROOT / "credentials.json").exists():
        print("[ERROR] 未找到 credentials.json，请参考 README")
        return
    from core.gmail import gmail_auth
    gmail_auth()


IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"


def _schedule_on(h, m):
    scripts = PROJECT_ROOT / "scripts"
    if IS_WINDOWS:
        subprocess.run([str(scripts / "setup_schedule.bat"), h, m], shell=True)
    elif IS_MACOS:
        subprocess.run(["bash", str(scripts / "setup_schedule.sh"), h, m])
    else:
        # Linux: use crontab
        entry = f"{m} {h} * * * cd {PROJECT_ROOT} && {sys.executable} launcher.py run --lite"
        subprocess.run(f'(crontab -l 2>/dev/null | grep -v "launcher.py"; echo "{entry}") | crontab -',
                       shell=True)
        print(f"[OK] crontab 已添加: {h}:{m}")


def _schedule_off():
    if IS_WINDOWS:
        subprocess.run(["schtasks", "/delete", "/tn", "QiuzhaoAgent", "/f"], capture_output=True)
    elif IS_MACOS:
        plist = Path.home() / "Library/LaunchAgents" / f"com.{os.environ.get('USER','user')}.qiuzhao-agent.plist"
        subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
    else:
        subprocess.run('crontab -l 2>/dev/null | grep -v "launcher.py" | crontab -', shell=True)
    print("[OK] 定时任务已关闭")


def cmd_schedule(args):
    sched = cfg.get_schedule_config()

    if "--on" in args:
        sched["enabled"] = True
        cfg.save_schedule_config(sched)
        h, m = sched["time"].split(":")
        _schedule_on(h, m)

    elif "--off" in args:
        sched["enabled"] = False
        cfg.save_schedule_config(sched)
        _schedule_off()

    elif "--time" in args:
        idx = args.index("--time")
        if idx + 1 < len(args):
            sched["time"] = args[idx + 1]
            cfg.save_schedule_config(sched)
            print(f"[OK] 执行时间: {sched['time']}")
            if sched["enabled"]:
                h, m = sched["time"].split(":")
                _schedule_on(h, m)
    else:
        platform = "Windows" if IS_WINDOWS else "macOS" if IS_MACOS else "Linux"
        print(f"定时: {'已启用' if sched['enabled'] else '未启用'} | {sched['time']} | {sched['mode']} | {platform}")
        print(f"邮箱: {'开' if sched['email'] else '关'} | 推送: {'开' if sched['push'] else '关'}")
        print("\n  --on / --off / --time HH:MM")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    commands = {
        "run": lambda: (
            setattr(__import__('core.daily', fromlist=['daily']), 'USE_LITE', '--lite' in rest),
            setattr(__import__('core.daily', fromlist=['daily']), 'SKIP_EMAIL', '--no-email' in rest or '--no-gmail' in rest),
            setattr(__import__('core.daily', fromlist=['daily']), 'SKIP_PUSH', '--no-push' in rest),
            cmd_run(),
        ),
        "init": cmd_init,
        "status": cmd_status,
        "test-push": cmd_test_push,
        "test-llm": cmd_test_llm,
        "gmail-auth": cmd_gmail_auth,
        "schedule": lambda: cmd_schedule(rest),
    }

    if cmd in commands:
        result = commands[cmd]
        result() if callable(result) else None
    else:
        print(f"未知命令: {cmd}\n")
        print(__doc__)


if __name__ == "__main__":
    main()
